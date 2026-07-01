#include "nightrider_event_frame_renderer/mono_event_frame_renderer.hpp"

#include <rclcpp/rclcpp.hpp>

#include <memory>

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<nightrider_event_frame_renderer::MonoEventFrameRenderer>(
    rclcpp::NodeOptions()));
  rclcpp::shutdown();
  return 0;
}
