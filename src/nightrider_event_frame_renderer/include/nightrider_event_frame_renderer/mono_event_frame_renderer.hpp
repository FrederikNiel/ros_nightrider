#ifndef NIGHTRIDER_EVENT_FRAME_RENDERER__MONO_EVENT_FRAME_RENDERER_HPP_
#define NIGHTRIDER_EVENT_FRAME_RENDERER__MONO_EVENT_FRAME_RENDERER_HPP_

#include <event_camera_codecs/decoder_factory.h>
#include <event_camera_codecs/event_processor.h>
#include <event_camera_msgs/msg/event_packet.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/compressed_image.hpp>
#include <sensor_msgs/msg/image.hpp>

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace nightrider_event_frame_renderer
{

class MonoEventFrameRenderer final
: public rclcpp::Node,
  public event_camera_codecs::EventProcessor
{
public:
  explicit MonoEventFrameRenderer(const rclcpp::NodeOptions & options);

  void eventCD(uint64_t sensor_time, uint16_t x, uint16_t y, uint8_t polarity) override;
  bool eventExtTrigger(uint64_t, uint8_t, uint8_t) override { return true; }
  void finished() override {}
  void rawData(const char *, size_t) override {}

private:
  using EventPacket = event_camera_msgs::msg::EventPacket;

  void eventPacketCallback(const EventPacket::ConstSharedPtr msg);
  void publishFrame();
  void resetFrame();
  void initializeFromPacket(const EventPacket & msg);

  rclcpp::Subscription<EventPacket>::SharedPtr eventSub_;
  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr imagePub_;
  rclcpp::Publisher<sensor_msgs::msg::CompressedImage>::SharedPtr compressedPub_;
  rclcpp::TimerBase::SharedPtr frameTimer_;

  event_camera_codecs::DecoderFactory<EventPacket, MonoEventFrameRenderer> decoderFactory_;
  std::shared_ptr<event_camera_codecs::Decoder<EventPacket, MonoEventFrameRenderer>> decoder_;

  sensor_msgs::msg::Image imageTemplate_;
  std::vector<uint8_t> frame_;

  double fps_{10.0};
  uint8_t noEventValue_{127};
  bool publishCompressed_{true};
  int pngCompressionLevel_{3};
  std::string compressedFormat_{"mono8; png compressed"};

  bool initialized_{false};
  bool frameHasEvents_{false};
};

}  // namespace nightrider_event_frame_renderer

#endif  // NIGHTRIDER_EVENT_FRAME_RENDERER__MONO_EVENT_FRAME_RENDERER_HPP_
