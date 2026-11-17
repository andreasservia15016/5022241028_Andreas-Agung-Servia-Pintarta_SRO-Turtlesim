#!/usr/bin/env python3
import math
import random
import rospy
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
from turtle_mission.msg import WallSensor


def normalize_angle(angle):
    """Menormalisasi sudut ke rentang [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class SafeExplorer:
    def __init__(self):
        rospy.init_node('safe_explorer', anonymous=False)

        # Parameter gerak eksplorasi dan penghindaran dinding
        self.cruise_speed = rospy.get_param('~cruise_speed', 2.0)
        self.avoid_speed = rospy.get_param('~avoid_speed', 0.6)
        self.kp_ang = rospy.get_param('~kp_ang', 4.5)
        self.center_x = 5.54
        self.center_y = 5.54

        self.current_pose = None
        self.sensor_data = None

        # Variabel untuk variasi belok acak saat mode jelajah aman
        self.random_angular = 0.0
        self.last_turn_change = rospy.Time.now()
        self.turn_interval = rospy.Duration(1.5)  # Ganti arah acak setiap 1.5 detik

        # Publisher kecepatan ke turtle1
        self.cmd_pub = rospy.Publisher('/turtle1/cmd_vel', Twist, queue_size=10)

        # Subscriber pose dan sensor dinding
        rospy.Subscriber('/turtle1/pose', Pose, self.pose_callback)
        rospy.Subscriber('/wall_sensor', WallSensor, self.sensor_callback)

        rospy.loginfo("Safe Explorer siap menjelajah arena secara otonom.")

    def pose_callback(self, msg):
        self.current_pose = msg

    def sensor_callback(self, msg):
        self.sensor_data = msg

    def control_loop(self):
        rate = rospy.Rate(20)  # 20 Hz

        while not rospy.is_shutdown():
            if self.current_pose is None or self.sensor_data is None:
                rate.sleep()
                continue

            cmd = Twist()

            if self.sensor_data.near_wall:
                # MODE MENGHINDAR: Arahkan turtle kembali menuju pusat arena (5.54, 5.54)
                dx = self.center_x - self.current_pose.x
                dy = self.center_y - self.current_pose.y
                angle_to_center = math.atan2(dy, dx)
                angle_error = normalize_angle(angle_to_center - self.current_pose.theta)

                # Jika sudut hadap masih membelakangi pusat, kurangi laju maju drastis sambil berputar
                if abs(angle_error) > 0.5:
                    cmd.linear.x = 0.2
                else:
                    cmd.linear.x = self.avoid_speed

                cmd.angular.z = max(-4.0, min(4.0, self.kp_ang * angle_error))
                rospy.loginfo_throttle(1.0, "Dinding terdeteksi dekat! Menghindar ke pusat arena...")
            else:
                # MODE JELAJAH AMAN: Bergerak maju dengan variasi kecepatan sudut acak
                now = rospy.Time.now()
                if (now - self.last_turn_change) >= self.turn_interval:
                    self.random_angular = random.uniform(-1.8, 1.8)
                    self.turn_interval = rospy.Duration(random.uniform(1.0, 2.5))
                    self.last_turn_change = now

                cmd.linear.x = self.cruise_speed
                cmd.angular.z = self.random_angular

            self.cmd_pub.publish(cmd)
            rate.sleep()


if __name__ == '__main__':
    try:
        explorer = SafeExplorer()
        explorer.control_loop()
    except rospy.ROSInterruptException:
        pass
