#!/usr/bin/env python3

import json
import math
from collections import defaultdict, deque

import rclpy
from event_camera_msgs.msg import EventPacket
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy
from std_msgs.msg import String


ADDR_X = 0x2
VECT_BASE_X = 0x3
VECT_12 = 0x4
VECT_8 = 0x5
TIME_LOW = 0x6
TIME_HIGH = 0x8


class Evt3Counter:
    def __init__(self, bucket_ns):
        self.bucket_ns = bucket_ns
        self.time_low = 0
        self.time_high = 0
        self.has_valid_time = False
        self.has_valid_high_time = False
        self.current_polarity = 0
        self.counts = defaultdict(lambda: [0, 0])
        self.first_time_ns = None
        self.last_time_ns = None
        self.last_bucket = None
        self.total_events = 0
        self.total_packets = 0

    def decode(self, msg):
        if msg.encoding.lower() != "evt3":
            raise ValueError(f"unsupported event encoding: {msg.encoding}")

        data = msg.events
        packet_events = 0
        packet_first_ns = None
        packet_last_ns = None

        for i in range(0, len(data) - 1, 2):
            word = data[i] | (data[i + 1] << 8)
            code = word >> 12
            rest = word & 0x0FFF

            if code == TIME_LOW:
                self.time_low = rest
                if self.has_valid_high_time:
                    self.has_valid_time = True
            elif code == TIME_HIGH:
                self.time_high = self._update_high_time(rest)
                self.has_valid_high_time = True
            elif code == ADDR_X:
                polarity = (rest >> 11) & 0x1
                packet_events += self._count_event(polarity)
            elif code == VECT_BASE_X:
                self.current_polarity = (rest >> 11) & 0x1
            elif code == VECT_8:
                packet_events += self._count_events(self.current_polarity, (rest & 0xFF).bit_count())
            elif code == VECT_12:
                packet_events += self._count_events(self.current_polarity, rest.bit_count())

            if self.has_valid_time and code in (TIME_LOW, ADDR_X, VECT_8, VECT_12):
                t_ns = self._time_ns()
                packet_first_ns = t_ns if packet_first_ns is None else packet_first_ns
                packet_last_ns = t_ns

        self.total_packets += 1
        self.total_events += packet_events
        if packet_first_ns is not None:
            self.first_time_ns = packet_first_ns if self.first_time_ns is None else self.first_time_ns
            self.last_time_ns = packet_last_ns
            self.last_bucket = packet_last_ns // self.bucket_ns
        return packet_events

    def trim_before(self, min_bucket):
        for bucket in list(self.counts.keys()):
            if bucket < min_bucket:
                del self.counts[bucket]

    def _count_event(self, polarity):
        return self._count_events(polarity, 1)

    def _count_events(self, polarity, n_events):
        if n_events <= 0 or not self.has_valid_time:
            return 0
        bucket = self._time_ns() // self.bucket_ns
        self.counts[bucket][polarity] += n_events
        return n_events

    def _time_ns(self):
        return (self.time_high | self.time_low) * 1000

    def _update_high_time(self, t):
        last_high = (self.time_high >> 12) & ((1 << 12) - 1)
        if t < last_high and last_high - t > 10:
            self.time_high += 1 << 24
        return (self.time_high & ~((1 << 24) - 1)) | (t << 12)


class EventSyncMonitor(Node):
    def __init__(self):
        super().__init__("event_sync_monitor")

        self.camera_0_topic = self.declare_parameter(
            "camera_0_topic", "/event_camera1/events").value
        self.camera_1_topic = self.declare_parameter(
            "camera_1_topic", "/event_camera2/events").value
        self.bucket_us = int(self.declare_parameter("bucket_us", 1000).value)
        self.window_buckets = int(self.declare_parameter("window_buckets", 200).value)
        self.max_lag_us = int(self.declare_parameter("max_lag_us", 20000).value)
        self.max_offset_us = int(self.declare_parameter("max_offset_us", 1000).value)
        self.max_jitter_us = int(self.declare_parameter("max_jitter_us", 2000).value)
        self.min_correlation = float(self.declare_parameter("min_correlation", 0.75).value)
        self.min_events_per_window = int(
            self.declare_parameter("min_events_per_window", 100).value)
        self.report_period_s = float(self.declare_parameter("report_period_s", 1.0).value)
        self.polarity = self.declare_parameter("polarity", "on").value

        if self.bucket_us <= 0:
            raise ValueError("bucket_us must be positive")
        if self.window_buckets <= 2:
            raise ValueError("window_buckets must be greater than 2")

        self.bucket_ns = self.bucket_us * 1000
        self.max_lag_buckets = max(1, int(round(self.max_lag_us / self.bucket_us)))
        self.history = deque(maxlen=30)
        self.cameras = [Evt3Counter(self.bucket_ns), Evt3Counter(self.bucket_ns)]

        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.sub_0 = self.create_subscription(
            EventPacket, self.camera_0_topic, lambda msg: self.event_packet(0, msg), qos)
        self.sub_1 = self.create_subscription(
            EventPacket, self.camera_1_topic, lambda msg: self.event_packet(1, msg), qos)
        self.status_pub = self.create_publisher(String, "event_sync_status", 10)
        self.timer = self.create_timer(self.report_period_s, self.report)

        self.get_logger().info(
            "monitoring event sync: "
            f"{self.camera_0_topic} vs {self.camera_1_topic}, "
            f"{self.bucket_us} us buckets, {self.window_buckets} bucket window")

    def event_packet(self, camera_index, msg):
        try:
            self.cameras[camera_index].decode(msg)
        except ValueError as exc:
            self.get_logger().warn(str(exc), throttle_duration_sec=5.0)

    def report(self):
        estimate = self.estimate_offset()
        if estimate is None:
            status = {
                "status": "UNKNOWN",
                "reason": "waiting for enough correlated event data",
                "latest_sensor_delta_us": self.latest_sensor_delta_us(),
                "camera_0_packets": self.cameras[0].total_packets,
                "camera_1_packets": self.cameras[1].total_packets,
                "camera_0_events": self.cameras[0].total_events,
                "camera_1_events": self.cameras[1].total_events,
            }
        else:
            self.history.append(estimate["offset_us"])
            jitter_us = max(self.history) - min(self.history) if len(self.history) > 1 else 0
            synced = (
                abs(estimate["offset_us"]) <= self.max_offset_us
                and estimate["correlation"] >= self.min_correlation
                and jitter_us <= self.max_jitter_us
            )
            status = {
                "status": "SYNCED" if synced else "NOT_SYNCED",
                "offset_us": estimate["offset_us"],
                "correlation": round(estimate["correlation"], 4),
                "jitter_us": jitter_us,
                "latest_sensor_delta_us": self.latest_sensor_delta_us(),
                "window_events_camera_0": estimate["events_0"],
                "window_events_camera_1": estimate["events_1"],
            }

        msg = String()
        msg.data = json.dumps(status, separators=(",", ":"))
        self.status_pub.publish(msg)
        self.get_logger().info(msg.data)

    def latest_sensor_delta_us(self):
        if self.cameras[0].last_time_ns is None or self.cameras[1].last_time_ns is None:
            return None
        return int(round((self.cameras[1].last_time_ns - self.cameras[0].last_time_ns) / 1000))

    def estimate_offset(self):
        if self.cameras[0].last_bucket is None or self.cameras[1].last_bucket is None:
            return None

        end_bucket = min(self.cameras[0].last_bucket, self.cameras[1].last_bucket)
        start_bucket = end_bucket - self.window_buckets + 1
        trim_bucket = start_bucket - self.max_lag_buckets - self.window_buckets
        self.cameras[0].trim_before(trim_bucket)
        self.cameras[1].trim_before(trim_bucket)

        best = None
        for lag in range(-self.max_lag_buckets, self.max_lag_buckets + 1):
            seq_0 = []
            seq_1 = []
            for bucket in range(start_bucket, end_bucket + 1):
                seq_0.append(self.bucket_value(self.cameras[0].counts.get(bucket)))
                seq_1.append(self.bucket_value(self.cameras[1].counts.get(bucket + lag)))

            events_0 = sum(seq_0)
            events_1 = sum(seq_1)
            if events_0 < self.min_events_per_window or events_1 < self.min_events_per_window:
                continue

            corr = self.pearson(seq_0, seq_1)
            if corr is None:
                continue
            if best is None or corr > best["correlation"]:
                best = {
                    "offset_us": lag * self.bucket_us,
                    "correlation": corr,
                    "events_0": events_0,
                    "events_1": events_1,
                }
        return best

    def bucket_value(self, counts):
        if counts is None:
            return 0
        if self.polarity == "off":
            return counts[0]
        if self.polarity == "total":
            return counts[0] + counts[1]
        return counts[1]

    @staticmethod
    def pearson(xs, ys):
        n = len(xs)
        if n != len(ys) or n == 0:
            return None
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        cov = 0.0
        var_x = 0.0
        var_y = 0.0
        for x, y in zip(xs, ys):
            dx = x - mean_x
            dy = y - mean_y
            cov += dx * dy
            var_x += dx * dx
            var_y += dy * dy
        if var_x <= 0.0 or var_y <= 0.0:
            return None
        return cov / math.sqrt(var_x * var_y)


def main(args=None):
    rclpy.init(args=args)
    node = EventSyncMonitor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
