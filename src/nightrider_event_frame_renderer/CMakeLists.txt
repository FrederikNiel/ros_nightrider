cmake_minimum_required(VERSION 3.16)
project(nightrider_event_frame_renderer)

add_compile_options(-Wall -Wextra -Wpedantic)

find_package(ament_cmake REQUIRED)
find_package(event_camera_codecs REQUIRED)
find_package(event_camera_msgs REQUIRED)
find_package(image_transport REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(sensor_msgs REQUIRED)

add_library(mono_event_frame_renderer SHARED
  src/mono_event_frame_renderer.cpp)
target_include_directories(mono_event_frame_renderer PUBLIC
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  "$<INSTALL_INTERFACE:include>")
ament_target_dependencies(mono_event_frame_renderer
  event_camera_codecs
  event_camera_msgs
  image_transport
  rclcpp
  rclcpp_components
  sensor_msgs)

rclcpp_components_register_nodes(
  mono_event_frame_renderer
  "nightrider_event_frame_renderer::MonoEventFrameRenderer")

add_library(synced_dual_mono_event_frame_renderer SHARED
  src/synced_dual_mono_event_frame_renderer.cpp)
target_include_directories(synced_dual_mono_event_frame_renderer PUBLIC
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  "$<INSTALL_INTERFACE:include>")
ament_target_dependencies(synced_dual_mono_event_frame_renderer
  event_camera_codecs
  event_camera_msgs
  image_transport
  rclcpp
  rclcpp_components
  sensor_msgs)

rclcpp_components_register_nodes(
  synced_dual_mono_event_frame_renderer
  "nightrider_event_frame_renderer::SyncedDualMonoEventFrameRenderer")

add_executable(mono_event_frame_renderer_node
  src/mono_event_frame_renderer_node.cpp)
target_link_libraries(mono_event_frame_renderer_node
  mono_event_frame_renderer)
ament_target_dependencies(mono_event_frame_renderer_node
  rclcpp)

install(
  DIRECTORY include/
  DESTINATION include)

install(
  TARGETS
    mono_event_frame_renderer
    synced_dual_mono_event_frame_renderer
    mono_event_frame_renderer_node
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME})

ament_export_dependencies(
  event_camera_codecs
  event_camera_msgs
  image_transport
  rclcpp
  rclcpp_components
  sensor_msgs)
ament_export_include_directories(include)
ament_export_libraries(
  mono_event_frame_renderer
  synced_dual_mono_event_frame_renderer)

ament_package()
