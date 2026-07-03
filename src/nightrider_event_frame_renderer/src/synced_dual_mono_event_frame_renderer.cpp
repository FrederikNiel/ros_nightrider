#include "nightrider_event_frame_renderer/synced_dual_mono_event_frame_renderer.hpp"

#include <rclcpp_components/register_node_macro.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <functional>
#include <limits>
#include <stdexcept>

namespace nightrider_event_frame_renderer
{
namespace
{
uint8_t clampByte(int64_t value)
{
  return static_cast<uint8_t>(std::clamp<int64_t>(value, 0, 255));
}
}  // namespace

SyncedDualMonoEventFrameRenderer::SyncedDualMonoEventFrameRenderer(
  const rclcpp::NodeOptions & options)
: Node("synced_dual_mono_event_frame_renderer", options)
{
  fps_ = this->declare_parameter<double>("fps", 10.0);
  if (!std::isfinite(fps_) || fps_ <= 0.0) {
    throw std::runtime_error("fps must be positive");
  }
  framePeriodNs_ = static_cast<uint64_t>(std::llround(1.0e9 / fps_));
  if (framePeriodNs_ == 0) {
    throw std::runtime_error("fps produces a zero-length frame period");
  }

  noEventValue_ = clampByte(this->declare_parameter<int64_t>("no_event_value", 127));
  rotate180_ = this->declare_parameter<bool>("rotate_180", false);
  const auto queue_size = this->declare_parameter<int64_t>("max_queued_frames", 30);
  maxQueuedFrames_ = static_cast<size_t>(std::max<int64_t>(queue_size, 1));
  imageTopics_[0] = this->declare_parameter<std::string>(
    "camera_0_image_topic", "camera_0/image_raw");
  imageTopics_[1] = this->declare_parameter<std::string>(
    "camera_1_image_topic", "camera_1/image_raw");
  stampBaseNs_ = static_cast<uint64_t>(
    std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::system_clock::now().time_since_epoch())
      .count());

  const auto qos = rclcpp::QoS(rclcpp::KeepLast(1)).best_effort().durability_volatile();
  cameras_[0].eventSub = this->create_subscription<EventPacket>(
    "camera_0/events", qos,
    [this](const EventPacket::ConstSharedPtr msg) { eventPacketCallback(0, msg); });
  cameras_[1].eventSub = this->create_subscription<EventPacket>(
    "camera_1/events", qos,
    [this](const EventPacket::ConstSharedPtr msg) { eventPacketCallback(1, msg); });

  cameras_[0].imagePub = image_transport::create_publisher(
    this, imageTopics_[0], qos.get_rmw_qos_profile());
  cameras_[1].imagePub = image_transport::create_publisher(
    this, imageTopics_[1], qos.get_rmw_qos_profile());

  RCLCPP_INFO(
    this->get_logger(),
    "synced_dual_mono_event_frame_renderer publishing paired mono8 at %.3f Hz on %s and %s",
    fps_, imageTopics_[0].c_str(), imageTopics_[1].c_str());
}

void SyncedDualMonoEventFrameRenderer::initializeFromPacket(
  size_t camera_index, const EventPacket & msg)
{
  auto & camera = cameras_[camera_index];
  camera.decoder = camera.decoderFactory.newInstance(msg);
  if (!camera.decoder) {
    RCLCPP_ERROR(
      this->get_logger(), "unsupported event encoding on camera %zu: %s",
      camera_index, msg.encoding.c_str());
    throw std::runtime_error("unsupported event encoding");
  }

  camera.imageTemplate.header = msg.header;
  camera.imageTemplate.height = msg.height;
  camera.imageTemplate.width = msg.width;
  camera.imageTemplate.encoding = "mono8";
  camera.imageTemplate.is_bigendian = false;
  camera.imageTemplate.step = camera.imageTemplate.width;
  camera.currentFrame.assign(
    camera.imageTemplate.height * camera.imageTemplate.step, noEventValue_);
  camera.initialized = true;

  RCLCPP_INFO(
    this->get_logger(),
    "initialized synced mono event frame stream %zu: %u x %u, encoding %s",
    camera_index, camera.imageTemplate.width, camera.imageTemplate.height,
    msg.encoding.c_str());
}

void SyncedDualMonoEventFrameRenderer::eventPacketCallback(
  size_t camera_index, const EventPacket::ConstSharedPtr msg)
{
  std::lock_guard<std::mutex> lock(mutex_);
  auto & camera = cameras_[camera_index];
  if (!camera.initialized) {
    initializeFromPacket(camera_index, *msg);
  } else if (
    camera.imageTemplate.height != msg->height ||
    camera.imageTemplate.width != msg->width || !camera.decoder) {
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 5000,
      "ignoring event packet with changed sensor size on camera %zu", camera_index);
    return;
  }

  activeCamera_ = static_cast<int>(camera_index);
  uint64_t next_time = 0;
  while (camera.decoder->decodeUntil(
      *msg, this, std::numeric_limits<uint64_t>::max(), &next_time)) {
  }
  activeCamera_ = -1;

  publishReadyFrames();
}

void SyncedDualMonoEventFrameRenderer::eventCD(
  uint64_t sensor_time, uint16_t x, uint16_t y, uint8_t polarity)
{
  if (activeCamera_ < 0 || activeCamera_ >= static_cast<int>(cameras_.size())) {
    return;
  }

  auto & camera = cameras_[static_cast<size_t>(activeCamera_)];
  if (
    x >= camera.imageTemplate.width || y >= camera.imageTemplate.height ||
    camera.currentFrame.empty()) {
    return;
  }

  const uint64_t sensor_bin = sensor_time / framePeriodNs_;
  if (!camera.hasOriginBin) {
    camera.originBin = sensor_bin;
    camera.hasOriginBin = true;
    RCLCPP_INFO(
      this->get_logger(), "camera %d synced frame origin bin: %lu",
      activeCamera_, camera.originBin);
  }
  if (sensor_bin < camera.originBin) {
    return;
  }

  const uint64_t relative_bin = sensor_bin - camera.originBin;
  if (!advanceToBin(camera, relative_bin)) {
    return;
  }

  const auto image_x = rotate180_ ? camera.imageTemplate.width - 1U - x : x;
  const auto image_y = rotate180_ ? camera.imageTemplate.height - 1U - y : y;
  camera.currentFrame[
    static_cast<size_t>(image_y) * camera.imageTemplate.step + image_x] =
    polarity ? 255 : 0;
}

bool SyncedDualMonoEventFrameRenderer::advanceToBin(CameraState & camera, uint64_t bin)
{
  if (!camera.hasCurrentBin) {
    camera.currentBin = bin;
    resetFrame(camera.currentFrame);
    camera.hasCurrentBin = true;
    return true;
  }

  if (bin < camera.currentBin) {
    return false;
  }

  if (bin - camera.currentBin > maxQueuedFrames_) {
    queueCompletedFrame(camera, camera.currentBin);
    camera.currentBin = bin;
    resetFrame(camera.currentFrame);
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 5000,
      "skipping empty synced mono frame bins after a long event gap");
    return true;
  }

  while (camera.currentBin < bin) {
    queueCompletedFrame(camera, camera.currentBin);
    camera.currentBin++;
    resetFrame(camera.currentFrame);
  }
  return true;
}

void SyncedDualMonoEventFrameRenderer::queueCompletedFrame(
  CameraState & camera, uint64_t bin)
{
  camera.completedFrames[bin] = camera.currentFrame;
  while (camera.completedFrames.size() > maxQueuedFrames_) {
    camera.completedFrames.erase(camera.completedFrames.begin());
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 5000,
      "dropping old synced mono frame; increase max_queued_frames if streams are delayed");
  }
}

void SyncedDualMonoEventFrameRenderer::publishReadyFrames()
{
  auto & camera_0 = cameras_[0];
  auto & camera_1 = cameras_[1];

  while (!camera_0.completedFrames.empty() && !camera_1.completedFrames.empty()) {
    const uint64_t bin_0 = camera_0.completedFrames.begin()->first;
    const uint64_t bin_1 = camera_1.completedFrames.begin()->first;

    if (bin_0 == bin_1) {
      publishFrame(0, bin_0, camera_0.completedFrames.begin()->second);
      publishFrame(1, bin_1, camera_1.completedFrames.begin()->second);
      camera_0.completedFrames.erase(camera_0.completedFrames.begin());
      camera_1.completedFrames.erase(camera_1.completedFrames.begin());
    } else if (bin_0 < bin_1) {
      camera_0.completedFrames.erase(camera_0.completedFrames.begin());
      RCLCPP_WARN_THROTTLE(
        this->get_logger(), *this->get_clock(), 5000,
        "dropping unmatched camera 0 mono frame while waiting for synchronized bins");
    } else {
      camera_1.completedFrames.erase(camera_1.completedFrames.begin());
      RCLCPP_WARN_THROTTLE(
        this->get_logger(), *this->get_clock(), 5000,
        "dropping unmatched camera 1 mono frame while waiting for synchronized bins");
    }
  }
}

void SyncedDualMonoEventFrameRenderer::publishFrame(
  size_t camera_index, uint64_t bin, const std::vector<uint8_t> & frame)
{
  auto & camera = cameras_[camera_index];
  if (camera.imagePub.getNumSubscribers() == 0) {
    return;
  }

  sensor_msgs::msg::Image image = camera.imageTemplate;
  image.header.stamp = stampFromBin(bin);
  image.data = frame;
  camera.imagePub.publish(image);
}

void SyncedDualMonoEventFrameRenderer::resetFrame(std::vector<uint8_t> & frame) const
{
  std::fill(frame.begin(), frame.end(), noEventValue_);
}

builtin_interfaces::msg::Time SyncedDualMonoEventFrameRenderer::stampFromBin(
  uint64_t bin) const
{
  constexpr uint64_t nsec_per_sec = 1000000000ULL;
  const uint64_t max_stamp_ns =
    static_cast<uint64_t>(std::numeric_limits<int32_t>::max()) * nsec_per_sec +
    (nsec_per_sec - 1);
  uint64_t stamp_ns = max_stamp_ns;
  if (bin <= (max_stamp_ns - stampBaseNs_) / framePeriodNs_) {
    stamp_ns = stampBaseNs_ + bin * framePeriodNs_;
  }
  builtin_interfaces::msg::Time stamp;
  stamp.sec = static_cast<int32_t>(stamp_ns / nsec_per_sec);
  stamp.nanosec = static_cast<uint32_t>(stamp_ns % nsec_per_sec);
  return stamp;
}

}  // namespace nightrider_event_frame_renderer

RCLCPP_COMPONENTS_REGISTER_NODE(
  nightrider_event_frame_renderer::SyncedDualMonoEventFrameRenderer)
