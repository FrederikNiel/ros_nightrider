#include "nightrider_event_frame_renderer/mono_event_frame_renderer.hpp"

#include <opencv2/imgcodecs.hpp>
#include <rclcpp_components/register_node_macro.hpp>

#include <algorithm>
#include <chrono>
#include <functional>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace nightrider_event_frame_renderer
{
namespace
{
uint8_t clampByte(int value)
{
  return static_cast<uint8_t>(std::clamp(value, 0, 255));
}
}  // namespace

MonoEventFrameRenderer::MonoEventFrameRenderer(const rclcpp::NodeOptions & options)
: Node("mono_event_frame_renderer", options)
{
  fps_ = this->declare_parameter<double>("fps", 10.0);
  if (!std::isfinite(fps_) || fps_ <= 0.0) {
    throw std::runtime_error("fps must be positive");
  }

  noEventValue_ = clampByte(this->declare_parameter<int>("no_event_value", 127));
  publishCompressed_ = this->declare_parameter<bool>("publish_compressed", true);
  pngCompressionLevel_ = std::clamp(this->declare_parameter<int>("png_compression_level", 3), 0, 9);

  const auto qos = rclcpp::QoS(rclcpp::KeepLast(1)).best_effort().durability_volatile();
  eventSub_ = this->create_subscription<EventPacket>(
    "~/events", qos, std::bind(&MonoEventFrameRenderer::eventPacketCallback, this, std::placeholders::_1));
  imagePub_ = this->create_publisher<sensor_msgs::msg::Image>("~/image_raw", qos);
  if (publishCompressed_) {
    compressedPub_ =
      this->create_publisher<sensor_msgs::msg::CompressedImage>("~/image_raw/compressed", qos);
  }

  frameTimer_ = this->create_wall_timer(
    std::chrono::duration<double>(1.0 / fps_),
    std::bind(&MonoEventFrameRenderer::publishFrame, this));

  RCLCPP_INFO(
    this->get_logger(), "mono_event_frame_renderer publishing mono8 at %.3f Hz", fps_);
}

void MonoEventFrameRenderer::initializeFromPacket(const EventPacket & msg)
{
  decoder_ = decoderFactory_.newInstance(msg);
  if (!decoder_) {
    RCLCPP_ERROR(this->get_logger(), "unsupported event encoding: %s", msg.encoding.c_str());
    throw std::runtime_error("unsupported event encoding");
  }

  imageTemplate_.header = msg.header;
  imageTemplate_.height = msg.height;
  imageTemplate_.width = msg.width;
  imageTemplate_.encoding = "mono8";
  imageTemplate_.is_bigendian = false;
  imageTemplate_.step = imageTemplate_.width;

  frame_.assign(imageTemplate_.height * imageTemplate_.step, noEventValue_);
  initialized_ = true;

  RCLCPP_INFO(
    this->get_logger(), "initialized mono event frame stream: %u x %u, encoding %s",
    imageTemplate_.width, imageTemplate_.height, msg.encoding.c_str());
}

void MonoEventFrameRenderer::eventPacketCallback(const EventPacket::ConstSharedPtr msg)
{
  if (!initialized_) {
    initializeFromPacket(*msg);
  } else if (
    imageTemplate_.height != msg->height || imageTemplate_.width != msg->width ||
    !decoder_) {
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 5000,
      "ignoring event packet with changed sensor size");
    return;
  }

  uint64_t next_time = 0;
  decoder_->decodeUntil(*msg, this, std::numeric_limits<uint64_t>::max(), &next_time);
}

void MonoEventFrameRenderer::eventCD(
  uint64_t, uint16_t x, uint16_t y, uint8_t polarity)
{
  if (x >= imageTemplate_.width || y >= imageTemplate_.height || frame_.empty()) {
    return;
  }
  frame_[static_cast<size_t>(y) * imageTemplate_.step + x] = polarity ? 255 : 0;
  frameHasEvents_ = true;
}

void MonoEventFrameRenderer::publishFrame()
{
  if (!initialized_) {
    return;
  }

  sensor_msgs::msg::Image image = imageTemplate_;
  image.header.stamp = this->get_clock()->now();
  image.data = frame_;

  if (imagePub_->get_subscription_count() > 0) {
    imagePub_->publish(image);
  }

  if (publishCompressed_ && compressedPub_ && compressedPub_->get_subscription_count() > 0) {
    sensor_msgs::msg::CompressedImage compressed;
    compressed.header = image.header;
    compressed.format = compressedFormat_;

    const cv::Mat mono(
      static_cast<int>(image.height), static_cast<int>(image.width), CV_8UC1, image.data.data(),
      image.step);
    const std::vector<int> params = {cv::IMWRITE_PNG_COMPRESSION, pngCompressionLevel_};
    if (cv::imencode(".png", mono, compressed.data, params)) {
      compressedPub_->publish(std::move(compressed));
    } else {
      RCLCPP_WARN_THROTTLE(
        this->get_logger(), *this->get_clock(), 5000, "failed to PNG-compress mono event frame");
    }
  }

  if (frameHasEvents_) {
    resetFrame();
  }
}

void MonoEventFrameRenderer::resetFrame()
{
  std::fill(frame_.begin(), frame_.end(), noEventValue_);
  frameHasEvents_ = false;
}

}  // namespace nightrider_event_frame_renderer

RCLCPP_COMPONENTS_REGISTER_NODE(nightrider_event_frame_renderer::MonoEventFrameRenderer)
