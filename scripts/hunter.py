#!/usr/bin/env python3
# ==============================================================================
# Node: hunter.py
# Deskripsi:
# Node pengontrol otonom Level 3 (Hunter) untuk mengejar target di turtlesim.
# Mendukung 2 mode operasi:
# 1. Mode Otomatis: Target spawn acak secara otomatis terus menerus.
# 2. Mode Manual (User Interface): Target di-spawn berdasarkan input koordinat
#    atau klik dari hunter_gui (/hunter/spawn_coord).
# Dilengkapi P-Controller proporsional dan perubahan warna pena (Bonus).
# ==============================================================================

import math
import random
import rospy
from std_msgs.msg import String
from geometry_msgs.msg import Twist, Point
from turtlesim.msg import Pose
from turtlesim.srv import Spawn, Kill, SetPen
from turtle_mission.msg import Score


def normalize_angle(angle):
    """Menormalisasi sudut ke rentang [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class TurtleHunter:
    def __init__(self):
        rospy.init_node('hunter', anonymous=False)

        # Parameter P-Controller & perburuan
        self.kp_lin = rospy.get_param('~kp_lin', 2.0)
        self.kp_ang = rospy.get_param('~kp_ang', 6.5)
        self.catch_distance = rospy.get_param('~catch_distance', 0.5)
        self.max_lin_vel = rospy.get_param('~max_lin_vel', 3.0)
        self.max_ang_vel = rospy.get_param('~max_ang_vel', 4.5)
        self.max_targets = rospy.get_param('~max_targets', 0)  # 0 = tanpa batas (unlimited)
        self.auto_spawn = rospy.get_param('~auto_spawn', True)  # Default: True agar kompatibel

        # State hunter & target
        self.hunter_pose = None
        self.target_pose = None
        self.target_sub = None
        self.current_target_name = ""
        self.target_counter = 0
        self.score = 0
        self.start_time = rospy.Time.now()

        # Publisher kecepatan, skor, dan telemetri target
        self.cmd_pub = rospy.Publisher('/turtle1/cmd_vel', Twist, queue_size=10)
        self.score_pub = rospy.Publisher('/hunter/score', Score, queue_size=10)
        self.target_pose_pub = rospy.Publisher('/hunter/target_pose', Pose, queue_size=10)

        # Subscriber posisi hunter (turtle1)
        rospy.Subscriber('/turtle1/pose', Pose, self.hunter_pose_callback)

        # Subscriber untuk integrasi User Interface (GUI)
        rospy.Subscriber('/hunter/spawn_coord', Point, self.spawn_coord_callback)
        rospy.Subscriber('/hunter/set_mode', String, self.set_mode_callback)

        # Tunggu hingga seluruh service turtlesim tersedia
        rospy.loginfo("Menunggu service /spawn, /kill, dan /turtle1/set_pen...")
        rospy.wait_for_service('/spawn')
        rospy.wait_for_service('/kill')
        rospy.wait_for_service('/turtle1/set_pen')

        self.spawn_srv = rospy.ServiceProxy('/spawn', Spawn)
        self.kill_srv = rospy.ServiceProxy('/kill', Kill)
        self.pen_srv = rospy.ServiceProxy('/turtle1/set_pen', SetPen)

        rospy.loginfo("Hunter siap berburu! Mode awal auto_spawn: %s", str(self.auto_spawn))

    def hunter_pose_callback(self, msg):
        self.hunter_pose = msg

    def target_pose_callback(self, msg):
        self.target_pose = msg
        # Publikasikan ulang pose target agar UI dapat menampilkan posisi target
        self.target_pose_pub.publish(msg)

    def spawn_coord_callback(self, msg):
        """Menerima koordinat spawn dari User Interface."""
        if msg.z < 0:
            # Sinyal z = -1 menandakan spawn acak dari UI
            rospy.loginfo("[UI] Menerima request spawn acak.")
            self.spawn_new_target()
        else:
            rospy.loginfo("[UI] Menerima request spawn koordinat: (%.2f, %.2f)", msg.x, msg.y)
            self.spawn_new_target(msg.x, msg.y)

    def set_mode_callback(self, msg):
        """Mengubah mode perburuan (auto vs manual)."""
        mode = msg.data.strip().lower()
        if mode == "auto":
            self.auto_spawn = True
            rospy.loginfo("[UI] Mode Hunter diubah ke: OTOMATIS (Auto Spawn)")
            if not self.current_target_name:
                self.spawn_new_target()
        elif mode == "manual":
            self.auto_spawn = False
            rospy.loginfo("[UI] Mode Hunter diubah ke: MANUAL (Menunggu input lokasi UI)")

    def change_pen_color(self):
        """Bonus: Mengubah warna pena turtle1 secara acak setiap pergantian target."""
        try:
            r = random.randint(50, 255)
            g = random.randint(50, 255)
            b = random.randint(50, 255)
            self.pen_srv(r, g, b, 3, 0)
        except rospy.ServiceException as e:
            rospy.logwarn("Gagal mengubah warna pena: %s", e)

    def spawn_new_target(self, x=None, y=None):
        """Memunculkan turtle target baru di posisi koordinat yang diminta atau acak."""
        # Jika masih ada target aktif sebelumnya, hapus terlebih dahulu
        if self.current_target_name:
            try:
                self.kill_srv(self.current_target_name)
            except rospy.ServiceException:
                pass
            self.current_target_name = ""
            self.target_pose = None

        self.target_counter += 1
        target_name = f"target{self.target_counter}"

        if x is not None and y is not None:
            rx = float(x)
            ry = float(y)
            rtheta = 0.0
        else:
            # Koordinat acak antara 1.5 s/d 9.5 agar aman dari batas dinding luar
            rx = random.uniform(1.5, 9.5)
            ry = random.uniform(1.5, 9.5)
            rtheta = random.uniform(-math.pi, math.pi)

        # Batasi agar selalu di dalam arena Turtlesim (0.5 - 10.5)
        rx = max(0.5, min(10.5, rx))
        ry = max(0.5, min(10.5, ry))

        try:
            self.spawn_srv(rx, ry, rtheta, target_name)
            self.current_target_name = target_name
            self.target_pose = None

            # Putuskan subscriber target lama jika ada, lalu subscribe ke target baru
            if self.target_sub is not None:
                self.target_sub.unregister()
            self.target_sub = rospy.Subscriber(f"/{target_name}/pose", Pose, self.target_pose_callback)

            # Ubah warna pena sebagai penanda fase target baru (Bonus)
            self.change_pen_color()

            rospy.loginfo("Target baru muncul: %s di posisi (%.2f, %.2f)", target_name, rx, ry)
            return True
        except rospy.ServiceException as e:
            rospy.logerr("Gagal spawn target %s: %s", target_name, e)
            return False

    def kill_current_target(self):
        """Menghapus target yang tertangkap dan mempublikasikan skor terbaru."""
        if not self.current_target_name:
            return

        try:
            self.kill_srv(self.current_target_name)
            self.score += 1
            elapsed = (rospy.Time.now() - self.start_time).to_sec()

            score_msg = Score()
            score_msg.score = self.score
            score_msg.last_target = self.current_target_name
            score_msg.elapsed_time = elapsed
            self.score_pub.publish(score_msg)

            rospy.loginfo("TARGET TERTANGKAP (%s)! Total Skor: %d | Waktu: %.2f detik",
                          self.current_target_name, self.score, elapsed)

            self.current_target_name = ""
            self.target_pose = None
        except rospy.ServiceException as e:
            rospy.logerr("Gagal melakukan /kill pada %s: %s", self.current_target_name, e)

    def stop_hunter(self):
        cmd = Twist()
        self.cmd_pub.publish(cmd)

    def run(self):
        rate = rospy.Rate(20)  # 20 Hz

        # Tunggu pose awal turtle1 masuk
        while not rospy.is_shutdown() and self.hunter_pose is None:
            rate.sleep()

        # Spawn target awal jika mode auto_spawn aktif
        if self.auto_spawn:
            self.spawn_new_target()

        while not rospy.is_shutdown():
            # Cek batas maksimum target jika dikonfigurasi > 0
            if self.max_targets > 0 and self.score >= self.max_targets:
                self.stop_hunter()
                rospy.loginfo("Misi Hunter selesai! Total skor: %d", self.score)
                break

            # Jika belum ada target aktif
            if not self.current_target_name:
                if self.auto_spawn:
                    self.spawn_new_target()
                else:
                    self.stop_hunter()
                rate.sleep()
                continue

            # Tunggu hingga pose target diterima
            if self.hunter_pose is None or self.target_pose is None:
                rate.sleep()
                continue

            # Hitung jarak Euclidean antara hunter dan target
            dx = self.target_pose.x - self.hunter_pose.x
            dy = self.target_pose.y - self.hunter_pose.y
            distance = math.sqrt(dx**2 + dy**2)

            if distance < self.catch_distance:
                # Target tertangkap!
                self.stop_hunter()
                self.kill_current_target()
                rospy.sleep(0.2)  # Jeda singkat sebelum spawn berikutnya

                # Jika mode auto_spawn aktif, otomatis spawn target baru
                if self.auto_spawn:
                    if self.max_targets == 0 or self.score < self.max_targets:
                        self.spawn_new_target()
                else:
                    rospy.loginfo("[MODE MANUAL] Target tertangkap! Menunggu input koordinat spawn berikutnya...")
            else:
                # Kejar target menggunakan P-Controller
                target_angle = math.atan2(dy, dx)
                angle_error = normalize_angle(target_angle - self.hunter_pose.theta)

                cmd = Twist()
                if abs(angle_error) > 0.4:
                    cmd.linear.x = 0.2
                else:
                    cmd.linear.x = self.kp_lin * distance

                cmd.angular.z = self.kp_ang * angle_error

                # Pembatasan kecepatan maksimum (clamping)
                cmd.linear.x = max(-self.max_lin_vel, min(self.max_lin_vel, cmd.linear.x))
                cmd.angular.z = max(-self.max_ang_vel, min(self.max_ang_vel, cmd.angular.z))

                self.cmd_pub.publish(cmd)

            rate.sleep()


if __name__ == '__main__':
    try:
        hunter = TurtleHunter()
        hunter.run()
    except rospy.ROSInterruptException:
        pass
