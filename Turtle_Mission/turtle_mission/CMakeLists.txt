cmake_minimum_required(VERSION 3.0.2)
project(turtle_mission)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  message_generation
  rospy
  std_msgs
  turtlesim
)

## Deklarasi seluruh file custom message (.msg)
add_message_files(
  FILES
  MissionStatus.msg
  WallSensor.msg
  Score.msg
)

## Deklarasi file custom service (.srv)
add_service_files(
  FILES
  StartMission.srv
)

## Generate messages dan services
generate_messages(
  DEPENDENCIES
  geometry_msgs
  std_msgs
)

## Konfigurasi catkin package
catkin_package(
  CATKIN_DEPENDS geometry_msgs message_runtime rospy std_msgs turtlesim
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)

## Instalasi seluruh script Python (Level 1, 2, & 3)
catkin_install_python(PROGRAMS
  scripts/mission_manager.py
  scripts/waypoint_controller.py
  scripts/wall_sensor.py
  scripts/safe_explorer.py
  scripts/hunter.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
