#!/usr/bin/env python3
import rospy
from turtlesim.msg import Pose
from turtle_mission.msg import WallSensor


class WallSensorNode:
    def __init__(self):
        rospy.init_node('wall_sensor', anonymous=False)

        # Dimensi default arena turtlesim adalah 0.0 sampai 11.08
        self.arena_min = rospy.get_param('~arena_min', 0.0)
        self.arena_max = rospy.get_param('~arena_max', 11.08)
        self.threshold = rospy.get_param('~safe_distance', 1.0)

        self.current_pose = None

        # Publisher data sensor virtual ke topic /wall_sensor
        self.sensor_pub = rospy.Publisher('/wall_sensor', WallSensor, queue_size=10)

        # Subscriber posisi turtle1
        rospy.Subscriber('/turtle1/pose', Pose, self.pose_callback)

        rospy.loginfo("Wall Sensor virtual aktif (Batas aman: %.2f unit).", self.threshold)

    def pose_callback(self, msg):
        self.current_pose = msg

    def run(self):
        rate = rospy.Rate(20)  # Update sensor 20 Hz agar responsif
        while not rospy.is_shutdown():
            if self.current_pose is not None:
                sensor_msg = WallSensor()

                # Hitung jarak ke masing-masing dinding
                sensor_msg.dist_left = max(0.0, self.current_pose.x - self.arena_min)
                sensor_msg.dist_right = max(0.0, self.arena_max - self.current_pose.x)
                sensor_msg.dist_bottom = max(0.0, self.current_pose.y - self.arena_min)
                sensor_msg.dist_top = max(0.0, self.arena_max - self.current_pose.y)

                # Cari jarak terdekat ke dinding mana pun
                min_dist = min(
                    sensor_msg.dist_left,
                    sensor_msg.dist_right,
                    sensor_msg.dist_bottom,
                    sensor_msg.dist_top
                )

                # Set flag bahaya jika jarak minimum < 1.0 unit
                sensor_msg.near_wall = bool(min_dist < self.threshold)

                self.sensor_pub.publish(sensor_msg)

            rate.sleep()


if __name__ == '__main__':
    try:
        node = WallSensorNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
