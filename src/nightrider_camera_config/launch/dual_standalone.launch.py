from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
import os


def make_driver(name, serial, bias_file):
    return ComposableNode(
        package="metavision_driver",
        plugin="metavision_driver::DriverROS2",
        name=name,
        parameters=[
            {
                "serial": serial,
                "sync_mode": "standalone",
                "bias_file": bias_file,
                "erc_mode": "enabled",
                "erc_rate": 1000000,
                "event_message_time_threshold": 0.001,
                "send_queue_size": 1,
                "use_multithreading": False,
            }
        ],
        remappings=[("~/events", f"{name}/events")],
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


def launch_setup(context):
    camera_0_name = LaunchConfiguration("camera_0_name").perform(context)
    camera_1_name = LaunchConfiguration("camera_1_name").perform(context)
    camera_0_serial = LaunchConfiguration("camera_0_serial").perform(context)
    camera_1_serial = LaunchConfiguration("camera_1_serial").perform(context)
    with_renderer = LaunchConfiguration("with_renderer")

    bias_file = os.path.join(
        get_package_share_directory("nightrider_camera_config"),
        "config",
        "imx636_low_rate.bias",
    )

    nodes = [
        make_driver(camera_0_name, camera_0_serial, bias_file),
        make_driver(camera_1_name, camera_1_serial, bias_file),
        make_renderer(camera_0_name),
        make_renderer(camera_1_name),
    ]

    return [
        ComposableNodeContainer(
            name="nightrider_dual_camera_container",
            namespace="",
            package="rclcpp_components",
            executable="component_container_isolated",
            composable_node_descriptions=nodes[:2],
            output="screen",
        ),
        ComposableNodeContainer(
            name="nightrider_renderer_container",
            namespace="",
            package="rclcpp_components",
            executable="component_container_isolated",
            composable_node_descriptions=nodes[2:],
            output="screen",
            condition=IfCondition(with_renderer),
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
            OpaqueFunction(function=launch_setup),
        ]
    )
