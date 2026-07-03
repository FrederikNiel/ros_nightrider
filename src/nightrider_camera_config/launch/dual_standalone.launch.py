from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import ExecuteProcess
from launch.actions import OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
import os
import sys


def make_driver(name, serial, bias_file, sync_mode="standalone", ready_camera_name=None):
    remappings = [("~/events", f"{name}/events")]
    if ready_camera_name is not None:
        remappings.append(("~/ready", f"{ready_camera_name}/ready"))

    return ComposableNode(
        package="metavision_driver",
        plugin="metavision_driver::DriverROS2",
        name=name,
        parameters=[
            {
                "serial": serial,
                "sync_mode": sync_mode,
                "bias_file": bias_file,
                "erc_mode": "enabled",
                "erc_rate": 1000000,
                "event_message_time_threshold": 0.001,
                "send_queue_size": 1,
                "use_multithreading": False,
            }
        ],
        remappings=remappings,
        extra_arguments=[{"use_intra_process_comms": True}],
    )


def make_renderer(name):
    return ComposableNode(
        package="event_camera_renderer",
        plugin="event_camera_renderer::Renderer",
        namespace=name,
        name="renderer",
        parameters=[
            {
                "fps": 10.0,
                "event_queue_memory_limit": 262144,
            }
        ],
        remappings=[("~/events", "events")],
        extra_arguments=[{"use_intra_process_comms": True}],
    )


def make_event_frame_renderer(name):
    return ComposableNode(
        package="nightrider_event_frame_renderer",
        plugin="nightrider_event_frame_renderer::MonoEventFrameRenderer",
        namespace=name,
        name="event_frame_mono",
        parameters=[
            {
                "fps": 10.0,
                "no_event_value": 127,
                "rotate_180": True,
                "image_raw.format": "png",
                "image_raw.png_level": 3,
            }
        ],
        remappings=[("~/events", "events")],
        extra_arguments=[{"use_intra_process_comms": True}],
    )


def make_synced_event_frame_renderer(camera_0_name, camera_1_name):
    parameters = {
        "fps": 10.0,
        "no_event_value": 127,
        "rotate_180": True,
        "max_queued_frames": 30,
        "image_raw.format": "png",
        "image_raw.png_level": 3,
        "camera_0.image_raw.format": "png",
        "camera_0.image_raw.png_level": 3,
        "camera_1.image_raw.format": "png",
        "camera_1.image_raw.png_level": 3,
        f"{camera_0_name}.image_raw.format": "png",
        f"{camera_0_name}.image_raw.png_level": 3,
        f"{camera_1_name}.image_raw.format": "png",
        f"{camera_1_name}.image_raw.png_level": 3,
    }

    return ComposableNode(
        package="nightrider_event_frame_renderer",
        plugin="nightrider_event_frame_renderer::SyncedDualMonoEventFrameRenderer",
        name="synced_event_frame_mono",
        parameters=[parameters],
        remappings=[
            ("camera_0/events", f"{camera_0_name}/events"),
            ("camera_1/events", f"{camera_1_name}/events"),
            ("camera_0/image_raw", f"{camera_0_name}/image_raw"),
            ("camera_1/image_raw", f"{camera_1_name}/image_raw"),
        ],
        extra_arguments=[{"use_intra_process_comms": True}],
    )


def make_sync_monitor(camera_0_name, camera_1_name, script_path, condition):
    return ExecuteProcess(
        cmd=[
            sys.executable,
            script_path,
            "--ros-args",
            "-r",
            "__node:=event_sync_monitor",
            "-p",
            f"camera_0_topic:=/{camera_0_name}/events",
            "-p",
            f"camera_1_topic:=/{camera_1_name}/events",
            "-p",
            "bucket_us:=1000",
            "-p",
            "window_buckets:=200",
            "-p",
            "max_lag_us:=20000",
            "-p",
            "max_offset_us:=1000",
            "-p",
            "max_jitter_us:=2000",
            "-p",
            "min_correlation:=0.75",
            "-p",
            "polarity:=on",
        ],
        output="screen",
        condition=condition,
    )


def launch_setup(context):
    camera_0_name = LaunchConfiguration("camera_0_name").perform(context)
    camera_1_name = LaunchConfiguration("camera_1_name").perform(context)
    camera_0_serial = LaunchConfiguration("camera_0_serial").perform(context)
    camera_1_serial = LaunchConfiguration("camera_1_serial").perform(context)
    with_renderer = LaunchConfiguration("with_renderer")
    with_event_frame_renderer = LaunchConfiguration("with_event_frame_renderer")
    with_test_iris = LaunchConfiguration("with_test_iris")
    with_synced_events = LaunchConfiguration("with_synced_events")
    with_sync_monitor = LaunchConfiguration("with_sync_monitor")
    synced_events = IfCondition(with_synced_events).evaluate(context)

    package_share = get_package_share_directory("nightrider_camera_config")
    bias_file = os.path.join(package_share, "config", "imx636_low_rate.bias")
    test_iris_script = os.path.join(package_share, "scripts", "test_iris.py")
    sync_monitor_script = os.path.join(package_share, "scripts", "event_sync_monitor.py")

    camera_nodes = [
        make_driver(
            camera_0_name,
            camera_0_serial,
            bias_file,
            "primary" if synced_events else "standalone",
            camera_1_name if synced_events else None,
        ),
        make_driver(
            camera_1_name,
            camera_1_serial,
            bias_file,
            "secondary" if synced_events else "standalone",
        ),
    ]
    renderer_nodes = [
        make_renderer(camera_0_name),
        make_renderer(camera_1_name),
    ]
    event_frame_nodes = (
        [make_synced_event_frame_renderer(camera_0_name, camera_1_name)]
        if synced_events
        else [
            make_event_frame_renderer(camera_0_name),
            make_event_frame_renderer(camera_1_name),
        ]
    )

    return [
        ComposableNodeContainer(
            name="nightrider_dual_camera_container",
            namespace="",
            package="rclcpp_components",
            executable="component_container_isolated",
            composable_node_descriptions=camera_nodes,
            output="screen",
        ),
        ComposableNodeContainer(
            name="nightrider_renderer_container",
            namespace="",
            package="rclcpp_components",
            executable="component_container_isolated",
            composable_node_descriptions=renderer_nodes,
            output="screen",
            condition=IfCondition(with_renderer),
        ),
        ComposableNodeContainer(
            name="nightrider_event_frame_container",
            namespace="",
            package="rclcpp_components",
            executable="component_container_isolated",
            composable_node_descriptions=event_frame_nodes,
            output="screen",
            condition=IfCondition(with_event_frame_renderer),
        ),
        ExecuteProcess(
            cmd=[sys.executable, test_iris_script],
            output="screen",
            condition=IfCondition(with_test_iris),
        ),
        make_sync_monitor(
            camera_0_name,
            camera_1_name,
            sync_monitor_script,
            IfCondition(with_sync_monitor),
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("camera_0_name", default_value="event_camera1"),
            DeclareLaunchArgument("camera_1_name", default_value="event_camera2"),
            DeclareLaunchArgument("camera_0_serial", default_value="4110047898"),
            DeclareLaunchArgument("camera_1_serial", default_value="4110049266"),
            DeclareLaunchArgument("with_renderer", default_value="true"),
            DeclareLaunchArgument("with_event_frame_renderer", default_value="true"),
            DeclareLaunchArgument("with_test_iris", default_value="true"),
            DeclareLaunchArgument("with_synced_events", default_value="false"),
            DeclareLaunchArgument("with_sync_monitor", default_value="false"),
            OpaqueFunction(function=launch_setup),
        ]
    )
