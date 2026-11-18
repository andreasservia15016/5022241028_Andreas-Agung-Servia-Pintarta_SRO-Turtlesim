cmake_minimum_required(VERSION 3.0.2)
project(turtle_mission)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  turtlesim
  message_generation
)

## Declare ROS messages and services
add_message_files(
  FILES
  MissionStatus.msg
  WallSensor.msg
  Score.msg
  CustomWallSensor.msg
)

add_service_files(
  FILES
  StartMission.srv
)

## Generate added messages and services with any dependencies listed here
generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs
)

## catkin_package declaration
catkin_package(
  CATKIN_DEPENDS
  rospy
  std_msgs
  geometry_msgs
  turtlesim
  message_runtime
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)

## Install python scripts
catkin_install_python(PROGRAMS
  scripts/mission_manager.py
  scripts/waypoint_controller.py
  scripts/wall_sensor.py
  scripts/safe_explorer.py
  scripts/hunter.py
  scripts/custom_wall_sensor.py
  scripts/custom_safe_explorer.py
  scripts/hunter_gui.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
