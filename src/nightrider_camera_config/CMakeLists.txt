cmake_minimum_required(VERSION 3.8)
project(nightrider_camera_config)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    ../test_iris.py
    scripts/event_sync_monitor.py
  DESTINATION share/${PROJECT_NAME}/scripts
)

install(
  PROGRAMS scripts/event_sync_monitor.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
