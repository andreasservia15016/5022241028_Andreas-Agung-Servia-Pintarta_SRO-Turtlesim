#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Point
from turtlesim.msg import Pose
from turtle_mission.msg import MissionStatus
from turtle_mission.srv import StartMission, StartMissionResponse


class MissionManager:
    def __init__(self):
        rospy.init_node('mission_manager', anonymous=False)

        # Membaca parameter dari file waypoints.yaml
        raw_waypoints = rospy.get_param('~waypoints', [[2.0, 2.0], [9.0, 2.0], [9.0, 9.0], [2.0, 9.0]])
        self.return_to_start = rospy.get_param('~return_to_start', True)

        self.waypoints = list(raw_waypoints)
        self.start_pose = None
        self.start_recorded = False

        # Variabel status misi
        self.mission_active = False
        self.mission_finished = False
        self.current_idx = 0
        self.waypoint_transition_lock = False

        # Publisher untuk mengirim target koordinat ke waypoint_controller
        self.goal_pub = rospy.Publisher('/mission/goal', Point, queue_size=10)
        # Publisher untuk informasi indeks waypoint ke controller
        self.meta_pub = rospy.Publisher('/mission/meta', MissionStatus, queue_size=10)

        # Subscriber untuk merekam posisi awal turtle1 dan memantau status controller
        rospy.Subscriber('/turtle1/pose', Pose, self.pose_callback)
        rospy.Subscriber('/mission/status', MissionStatus, self.status_callback)

        # Service untuk memulai misi
        self.start_srv = rospy.Service('/start_mission', StartMission, self.handle_start_mission)

        rospy.loginfo("Mission Manager siap. Total waypoint: %d", len(self.waypoints))
        rospy.loginfo("Panggil service /start_mission untuk memulai patroli.")

    def pose_callback(self, msg):
        # Simpan posisi awal turtle tepat sekali saat node pertama kali menerima pose
        if not self.start_recorded:
            self.start_pose = [msg.x, msg.y]
            self.start_recorded = True
            if self.return_to_start:
                self.waypoints.append(self.start_pose)
                rospy.loginfo("Mode return_to_start aktif. Titik awal [%.2f, %.2f] ditambahkan ke akhir rute.",
                              msg.x, msg.y)

    def handle_start_mission(self, req):
        if not req.start:
            return StartMissionResponse(success=False, message="Request start bernilai False. Misi tidak dijalankan.")

        if self.mission_active:
            return StartMissionResponse(success=False, message="Misi sedang berjalan!")

        if len(self.waypoints) == 0:
            return StartMissionResponse(success=False, message="Daftar waypoint kosong!")

        # Reset dan mulai misi dari waypoint pertama
        self.current_idx = 0
        self.mission_active = True
        self.mission_finished = False
        self.waypoint_transition_lock = False

        rospy.loginfo("=== MISI DIMULAI ===")
        self.publish_current_goal()
        return StartMissionResponse(success=True, message="Misi patroli waypoint berhasil dimulai.")

    def publish_current_goal(self):
        if self.current_idx < len(self.waypoints):
            wp = self.waypoints[self.current_idx]
            goal_msg = Point()
            goal_msg.x = float(wp[0])
            goal_msg.y = float(wp[1])
            goal_msg.z = 0.0  # z = 0 menandakan misi aktif

            self.goal_pub.publish(goal_msg)
            rospy.loginfo("Menuju Waypoint %d/%d -> (%.2f, %.2f)",
                          self.current_idx + 1, len(self.waypoints), goal_msg.x, goal_msg.y)
        else:
            # Semua waypoint selesai
            self.mission_active = False
            self.mission_finished = True
            stop_msg = Point()
            stop_msg.z = -1.0  # z = -1 sebagai sinyal misi selesai
            self.goal_pub.publish(stop_msg)
            rospy.loginfo("=== SEMUA WAYPOINT TERCAPAI. MISI SELESAI ===")

    def status_callback(self, msg):
        if not self.mission_active:
            return

        # Cek apakah controller melaporkan target saat ini sudah tercapai (state == "REACHED")
        if msg.state == "REACHED" and not self.waypoint_transition_lock:
            self.waypoint_transition_lock = True
            rospy.loginfo("Waypoint %d tercapai! (Sisa jarak: %.3f)", self.current_idx + 1, msg.distance_to_target)
            self.current_idx += 1
            self.publish_current_goal()
        elif msg.state == "RUNNING":
            # Buka kunci transisi setelah controller mulai bergerak menuju target baru
            self.waypoint_transition_lock = False

    def run(self):
        rate = rospy.Rate(10)  # 10 Hz
        while not rospy.is_shutdown():
            # Terus kirim metadata jumlah waypoint agar status selalu sinkron
            meta = MissionStatus()
            meta.current_waypoint = self.current_idx + 1 if self.mission_active else (len(self.waypoints) if self.mission_finished else 0)
            meta.total_waypoints = len(self.waypoints)
            meta.state = "RUNNING" if self.mission_active else ("FINISHED" if self.mission_finished else "IDLE")
            self.meta_pub.publish(meta)

            # Publikasikan ulang goal aktif secara berkala untuk mencegah paket hilang
            if self.mission_active and self.current_idx < len(self.waypoints):
                wp = self.waypoints[self.current_idx]
                goal_msg = Point(x=float(wp[0]), y=float(wp[1]), z=0.0)
                self.goal_pub.publish(goal_msg)

            rate.sleep()


if __name__ == '__main__':
    try:
        manager = MissionManager()
        manager.run()
    except rospy.ROSInterruptException:
        pass
