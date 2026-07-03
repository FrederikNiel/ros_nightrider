#ifndef NIGHTRIDER_EVENT_FRAME_RENDERER__SYNCED_DUAL_MONO_EVENT_FRAME_RENDERER_HPP_
#define NIGHTRIDER_EVENT_FRAME_RENDERER__SYNCED_DUAL_MONO_EVENT_FRAME_RENDERER_HPP_

#include <event_camera_codecs/decoder_factory.h>
#include <event_camera_codecs/event_processor.h>
#include <event_camera_msgs/msg/event_packet.hpp>
#include <builtin_interfaces/msg/time.hpp>
#include <image_transport/image_transport.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>

#include <array>
#include <cstdint>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace nightrider_event_frame_renderer
{

class SyncedDualMonoEventFrameRenderer final
: public rclcpp::Node,
  public event_camera_codecs::EventProcessor
{
public:
  explicit SyncedDualMonoEventFrameRenderer(const rclcpp::NodeOptions & options);

  void eventCD(uint64_t sensor_time, uint16_t x, uint16_t y, uint8_t polarity) override;
  bool eventExtTrigger(uint64_t, uint8_t, uint8_t) override { return true; }
  void finished() override {}
  void rawData(const char *, size_t) override {}

private:
  using EventPacket = event_camera_msgs::msg::EventPacket;
  using Decoder =
    event_camera_codecs::Decoder<EventPacket, SyncedDualMonoEventFrameRenderer>;
  using DecoderFactory =
    event_camera_codecs::DecoderFactory<EventPacket, SyncedDualMonoEventFrameRenderer>;

  struct CameraState
  {
    rclcpp::Subscription<EventPacket>::SharedPtr eventSub;
    image_transport::Publisher imagePub;
    DecoderFactory decoderFactory;
    std::shared_ptr<Decoder> decoder;
    sensor_msgs::msg::Image imageTemplate;
    std::vector<uint8_t> currentFrame;
    std::map<uint64_t, std::vector<uint8_t>> completedFrames;
    uint64_t originBin{0};
    uint64_t currentBin{0};
    bool hasOriginBin{false};
    bool hasCurrentBin{false};
    bool initialized{false};
  };

  void eventPacketCallback(size_t camera_index, const EventPacket::ConstSharedPtr msg);
  void initializeFromPacket(size_t camera_index, const EventPacket & msg);
  bool advanceToBin(CameraState & camera, uint64_t bin);
  void queueCompletedFrame(CameraState & camera, uint64_t bin);
  void publishReadyFrames();
  void publishFrame(size_t camera_index, uint64_t bin, const std::vector<uint8_t> & frame);
  void resetFrame(std::vector<uint8_t> & frame) const;
  builtin_interfaces::msg::Time stampFromBin(uint64_t bin) const;

  std::array<CameraState, 2> cameras_;
  std::array<std::string, 2> imageTopics_;
  std::mutex mutex_;

  double fps_{10.0};
  uint64_t framePeriodNs_{100000000};
  uint64_t stampBaseNs_{0};
  uint8_t noEventValue_{127};
  bool rotate180_{false};
  size_t maxQueuedFrames_{30};
  int activeCamera_{-1};
};

}  // namespace nightrider_event_frame_renderer

#endif  // NIGHTRIDER_EVENT_FRAME_RENDERER__SYNCED_DUAL_MONO_EVENT_FRAME_RENDERER_HPP_
