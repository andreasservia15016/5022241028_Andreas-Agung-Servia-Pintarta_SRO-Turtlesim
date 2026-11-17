#!/usr/bin/env python3
import math
import rospy
from geometry_msgs.msg import Twist, Point
from turtlesim.msg import Pose
from turtle_mission.msg import MissionStatus


def normalize_angle(angle):
    """Menormalisasi sudut ke rentang [-pi, pi] agar turtle berputar lewat jalur terpendek."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class WaypointController:
    def __init__(self):
        rospy.init_node('waypoint_controller', anonymous=False)

        # Parameter P-Controller yang dapat diubah lewat launch file atau rosparam
        self.kp_lin = rospy.get_param('~kp_lin', 1.5)
        self.kp_ang = rospy.get_param('~kp_ang', 6.0)
        self.tolerance = rospy.get_param('~tolerance', 0.08)  # Wajib < 0.1 unit
        self.max_lin_vel = rospy.get_param('~max_lin_vel', 2.5)
        self.max_ang_vel = rospy.get_param('~max_ang_vel', 4.0)
        self.angle_threshold = rospy.get_param('~angle_threshold', 0.35)  # ~20 derajat

        # State internal
        self.current_pose = None
        self.current_goal = None
        self.mission_state = "IDLE"
        self.current_wp_num = 0
        self.total_wp_num = 0

        # Publisher
        self.cmd_pub = rospy.Publisher('/turtle1/cmd_vel', Twist, queue_size=10)
        self.status_pub = rospy.Publisher('/mission/status', MissionStatus, queue_size=10)

        # Subscriber
        rospy.Subscriber('/turtle1/pose', Pose, self.pose_callback)
        rospy.Subscriber('/mission/goal', Point, self.goal_callback)
        rospy.Subscriber('/mission/meta', MissionStatus, self.meta_callback)

        rospy.loginfo("Waypoint Controller aktif (Kp_lin=%.2f, Kp_ang=%.2f, tol=%.2f)",
                      self.kp_lin, self.kp_ang, self.tolerance)

    def pose_callback(self, msg):
        self.current_pose = msg

    def meta_callback(self, msg):
        self.current_wp_num = msg.current_waypoint
        self.total_wp_num = msg.total_waypoints
        if msg.state == "FINISHED":
            self.mission_state = "FINISHED"

    def goal_callback(self, msg):
        if msg.z < 0:
            # Sinyal z = -1 menandakan seluruh misi selesai
            self.current_goal = None
            self.mission_state = "FINISHED"
            self.stop_turtle()
        else:
            # Menerima waypoint baru
            if self.current_goal is None or (self.current_goal.x != msg.x or self.current_goal.y != msg.y):
                self.current_goal = msg
                self.mission_state = "RUNNING"

    def stop_turtle(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_pub.publish(cmd)

    def control_loop(self):
        rate = rospy.Rate(10)  # Wajib publish status pada 10 Hz

        while not rospy.is_shutdown():
            status_msg = MissionStatus()
            status_msg.current_waypoint = self.current_wp_num
            status_msg.total_waypoints = self.total_wp_num

            if self.current_pose is not None and self.current_goal is not None and self.mission_state != "FINISHED":
                # 1. Hitung error jarak Euclidean
                dx = self.current_goal.x - self.current_pose.x
                dy = self.current_goal.y - self.current_pose.y
                distance = math.sqrt(dx**2 + dy**2)
                status_msg.distance_to_target = distance

                # 2. Cek apakah sudah masuk toleransi (< 0.1 unit)
                if distance < self.tolerance:
                    self.stop_turtle()
                    status_msg.state = "REACHED"
                else:
                    status_msg.state = "RUNNING"
                    # 3. Hitung error sudut menuju target
                    target_angle = math.atan2(dy, dx)
                    angle_error = normalize_angle(target_angle - self.current_pose.theta)

                    cmd = Twist()
                    # Putar di tempat terlebih dahulu jika error sudut masih besar agar lintasan lurus
                    if abs(angle_error) > self.angle_threshold:
                        cmd.linear.x = 0.0
                        cmd.angular.z = self.kp_ang * angle_error
                    else:
                        cmd.linear.x = self.kp_lin * distance
                        cmd.angular.z = self.kp_ang * angle_error

                    # 4. Pembatasan kecepatan maksimum (clamping)
                    cmd.linear.x = max(-self.max_lin_vel, min(self.max_lin_vel, cmd.linear.x))
                    cmd.angular.z = max(-self.max_ang_vel, min(self.max_ang_vel, cmd.angular.z))

                    self.cmd_pub.publish(cmd)
            else:
                # Kondisi IDLE atau FINISHED
                status_msg.distance_to_target = 0.0
                status_msg.state = self.mission_state
                self.stop_turtle()

            # Publikasikan status misi setiap siklus (10 Hz)
            self.status_pub.publish(status_msg)
            rate.sleep()


if __name__ == '__main__':
    try:
        controller = WaypointController()
        controller.control_loop()
    except rospy.ROSInterruptException:
        pass
