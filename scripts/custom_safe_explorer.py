#!/usr/bin/env python3
# ==============================================================================
# Node: custom_safe_explorer.py
# Fungsi:
# 1. Mengendalikan gerakan turtle1 di simulator Turtlesim secara otonom (closed-loop).
# 2. Dalam keadaan aman (tidak dekat dinding), turtle1 menjelajahi arena secara dinamis.
# 3. Saat mendeteksi dinding custom atau dinding luar arena (near_wall == True),
#    turtle1 secara otomatis berputar menjauhi obstacle menggunakan vektor escape angle
#    yang dihitung secara matematis oleh custom_wall_sensor.
# ==============================================================================

import math
import random
import rospy
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
from turtle_mission.msg import CustomWallSensor


def normalize_angle(angle):
    """Menormalisasi sudut ke rentang [-pi, pi] radian."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class CustomSafeExplorer:
    def __init__(self):
        rospy.init_node('custom_safe_explorer', anonymous=False)

        # Parameter kontrol gerak
        self.cruise_speed = rospy.get_param('~cruise_speed', 2.0)
        self.avoid_speed = rospy.get_param('~avoid_speed', 0.8)
        self.kp_ang = rospy.get_param('~kp_ang', 5.0)
        self.max_ang_vel = rospy.get_param('~max_ang_vel', 4.5)

        self.current_pose = None
        self.sensor_data = None

        # Variabel eksplorasi acak
        self.random_angular = 0.0
        self.last_turn_change = rospy.Time.now()
        self.turn_interval = rospy.Duration(random.uniform(1.2, 2.5))

        # Publisher kecepatan perintah ke turtle1
        self.cmd_pub = rospy.Publisher('/turtle1/cmd_vel', Twist, queue_size=10)

        # Subscriber pose dan data sensor dinding custom
        rospy.Subscriber('/turtle1/pose', Pose, self.pose_callback)
        rospy.Subscriber('/custom_wall_sensor', CustomWallSensor, self.sensor_callback)

        rospy.loginfo("Custom Safe Explorer aktif. Siap menjelajah dan menghindari dinding custom.")

    def pose_callback(self, msg):
        self.current_pose = msg

    def sensor_callback(self, msg):
        self.sensor_data = msg

    def control_loop(self):
        rate = rospy.Rate(20)  # 20 Hz kontrol loop

        while not rospy.is_shutdown():
            if self.current_pose is None or self.sensor_data is None:
                rate.sleep()
                continue

            cmd = Twist()

            if self.sensor_data.near_wall:
                # ==============================================================
                # MODE MENGHINDAR (OBSTACLE AVOIDANCE)
                # ==============================================================
                # Sudut escape adalah arah vektor yang menjauhi titik dinding terdekat
                escape_angle = self.sensor_data.escape_angle
                angle_error = normalize_angle(escape_angle - self.current_pose.theta)

                # Jika turtle masih menghadap ke arah dinding, perlambat atau berhenti maju
                if abs(angle_error) > 0.6:  # > ~35 derajat
                    if self.sensor_data.min_distance < 0.35:
                        cmd.linear.x = 0.0  # Sangat dekat, putar di tempat
                    else:
                        cmd.linear.x = 0.15
                else:
                    # Sudah menghadap ke arah aman (menjauh dari dinding), maju keluar
                    cmd.linear.x = self.avoid_speed

                # Hitung kecepatan putar dengan P-Controller proporsional terhadap angle_error
                angular_cmd = self.kp_ang * angle_error
                cmd.angular.z = max(-self.max_ang_vel, min(self.max_ang_vel, angular_cmd))

                rospy.loginfo_throttle(
                    1.0,
                    "[MENGHINDAR] Obstacle: %s | Jarak: %.2f m | Escape Angle: %.2f rad",
                    self.sensor_data.nearest_obstacle,
                    self.sensor_data.min_distance,
                    escape_angle
                )
            else:
                # ==============================================================
                # MODE JELAJAH AMAN (CRUISE EXPLORATION)
                # ==============================================================
                now = rospy.Time.now()
                if (now - self.last_turn_change) >= self.turn_interval:
                    self.random_angular = random.uniform(-1.5, 1.5)
                    self.turn_interval = rospy.Duration(random.uniform(1.2, 2.8))
                    self.last_turn_change = now

                cmd.linear.x = self.cruise_speed
                cmd.angular.z = self.random_angular

            self.cmd_pub.publish(cmd)
            rate.sleep()


if __name__ == '__main__':
    try:
        explorer = CustomSafeExplorer()
        explorer.control_loop()
    except rospy.ROSInterruptException:
        pass
