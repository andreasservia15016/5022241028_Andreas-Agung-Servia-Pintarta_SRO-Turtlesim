#!/usr/bin/env python3
# ==============================================================================
# Node: custom_wall_sensor.py
# Fungsi:
# 1. Menggambar dinding custom di layar Turtlesim sesuai titik-titik koordinat
#    yang diberikan secara berurutan pada file custom_walls.yaml.
# 2. Menghitung jarak minimum dan vektor penghindaran (escape angle) dari turtle1
#    ke segmen garis dinding custom dan ke batas arena turtlesim (0 - 11.08).
# 3. Mempublikasikan data sensor ke topic /custom_wall_sensor dan /wall_sensor.
# ==============================================================================

import math
import rospy
from turtlesim.msg import Pose
from turtlesim.srv import Spawn, Kill, SetPen, TeleportAbsolute
from turtle_mission.msg import CustomWallSensor, WallSensor


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    """
    Menghitung jarak terpendek dari titik (px, py) ke segmen garis (x1, y1) -> (x2, y2),
    beserta koordinat titik terdekat pada segmen tersebut.
    """
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy

    if length_sq < 1e-9:
        # Jika kedua titik pembentuk segmen sama persis
        closest_x = x1
        closest_y = y1
    else:
        # Proyeksi skalar t dari titik ke garis (dibatasi rentang 0.0 sampai 1.0)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

    dist = math.hypot(px - closest_x, py - closest_y)
    return dist, closest_x, closest_y


class CustomWallSensorNode:
    def __init__(self):
        rospy.init_node('custom_wall_sensor', anonymous=False)

        # 1. Baca parameter dari rosparam / custom_walls.yaml
        raw_points = rospy.get_param('~wall_points', [
            [2.5, 2.5],
            [4.5, 2.5],
            [4.5, 4.5],
            [2.5, 4.5]
        ])
        self.wall_points = [[float(p[0]), float(p[1])] for p in raw_points]
        self.closed_loop = rospy.get_param('~closed_loop', True)
        self.safe_distance = rospy.get_param('~safe_distance', 1.0)
        self.draw_wall = rospy.get_param('~draw_wall', True)
        self.wall_color = rospy.get_param('~wall_color', [255, 50, 50])
        self.wall_width = rospy.get_param('~wall_width', 5)

        # Batas arena default Turtlesim
        self.arena_min = rospy.get_param('~arena_min', 0.0)
        self.arena_max = rospy.get_param('~arena_max', 11.08)

        # Bentuk daftar segmen garis dari titik-titik berurutan
        self.segments = []
        if len(self.wall_points) >= 2:
            for i in range(len(self.wall_points) - 1):
                self.segments.append((self.wall_points[i], self.wall_points[i + 1]))
            if self.closed_loop:
                self.segments.append((self.wall_points[-1], self.wall_points[0]))

        self.current_pose = None

        # 2. Inisialisasi Publisher
        self.custom_sensor_pub = rospy.Publisher('/custom_wall_sensor', CustomWallSensor, queue_size=10)
        self.standard_sensor_pub = rospy.Publisher('/wall_sensor', WallSensor, queue_size=10)

        # 3. Subscriber posisi turtle1
        rospy.Subscriber('/turtle1/pose', Pose, self.pose_callback)

        rospy.loginfo("Custom Wall Sensor aktif.")
        rospy.loginfo("Total titik dinding: %d, Jumlah segmen: %d, Closed Loop: %s, Batas Aman: %.2f",
                      len(self.wall_points), len(self.segments), str(self.closed_loop), self.safe_distance)

        # 4. Gambar dinding di layar Turtlesim jika opsi draw_wall aktif
        if self.draw_wall and len(self.wall_points) >= 2:
            self.draw_walls_on_canvas()

    def pose_callback(self, msg):
        self.current_pose = msg

    def draw_walls_on_canvas(self):
        """
        Menggambar segmen garis dinding secara visual di layar simulator Turtlesim
        menggunakan turtle pembantu bernama 'wall_drawer' yang kemudian di-kill.
        Turtle1 sama sekali tidak menggunakan teleport/teleop.
        """
        rospy.loginfo("Menyiapkan visualisasi dinding di layar Turtlesim...")
        try:
            rospy.wait_for_service('/spawn', timeout=5.0)
            rospy.wait_for_service('/kill', timeout=5.0)

            spawn_srv = rospy.ServiceProxy('/spawn', Spawn)
            kill_srv = rospy.ServiceProxy('/kill', Kill)

            # Titik awal untuk spawn turtle pembantu
            p0 = self.wall_points[0]
            drawer_name = "wall_drawer"

            # Spawn turtle pembantu di titik pertama
            spawn_srv(p0[0], p0[1], 0.0, drawer_name)

            rospy.wait_for_service(f'/{drawer_name}/set_pen', timeout=5.0)
            rospy.wait_for_service(f'/{drawer_name}/teleport_absolute', timeout=5.0)

            set_pen = rospy.ServiceProxy(f'/{drawer_name}/set_pen', SetPen)
            teleport = rospy.ServiceProxy(f'/{drawer_name}/teleport_absolute', TeleportAbsolute)

            # Matikan pen dulu saat inisialisasi warna dan ketebalan
            r = int(self.wall_color[0])
            g = int(self.wall_color[1])
            b = int(self.wall_color[2])
            w = int(self.wall_width)

            # Hidupkan pen untuk mulai menggambar
            set_pen(r, g, b, w, 0)

            # Gambar segmen garis berurutan
            for p in self.wall_points[1:]:
                teleport(p[0], p[1], 0.0)

            # Jika loop tertutup, gambar kembali ke titik pertama
            if self.closed_loop:
                teleport(p0[0], p0[1], 0.0)

            # Hapus turtle pembantu setelah selesai menggambar (garis tetap tertinggal)
            kill_srv(drawer_name)
            rospy.loginfo("Visualisasi dinding custom berhasil digambar di simulator!")
        except Exception as e:
            rospy.logwarn("Gagal menggambar dinding di turtlesim: %s", str(e))

    def run(self):
        rate = rospy.Rate(20)  # Update sensor pada frekuensi 20 Hz
        while not rospy.is_shutdown():
            if self.current_pose is not None:
                px = self.current_pose.x
                py = self.current_pose.y

                # A. Hitung jarak ke batas luar arena turtlesim
                dist_left = max(0.0, px - self.arena_min)
                dist_right = max(0.0, self.arena_max - px)
                dist_bottom = max(0.0, py - self.arena_min)
                dist_top = max(0.0, self.arena_max - py)

                min_dist_arena = min(dist_left, dist_right, dist_bottom, dist_top)

                if min_dist_arena == dist_left:
                    arena_closest = (self.arena_min, py)
                elif min_dist_arena == dist_right:
                    arena_closest = (self.arena_max, py)
                elif min_dist_arena == dist_bottom:
                    arena_closest = (px, self.arena_min)
                else:
                    arena_closest = (px, self.arena_max)

                # B. Hitung jarak terpendek ke seluruh segmen dinding custom
                min_dist_custom = float('inf')
                custom_closest = (0.0, 0.0)

                for seg in self.segments:
                    d, cx, cy = point_to_segment_distance(
                        px, py, seg[0][0], seg[0][1], seg[1][0], seg[1][1]
                    )
                    if d < min_dist_custom:
                        min_dist_custom = d
                        custom_closest = (cx, cy)

                # C. Tentukan obstacle terdekat (apakah dinding custom atau dinding arena)
                if min_dist_custom < min_dist_arena:
                    overall_min = min_dist_custom
                    nearest_pt = custom_closest
                    nearest_type = "custom_wall"
                else:
                    overall_min = min_dist_arena
                    nearest_pt = arena_closest
                    nearest_type = "arena_wall"

                # Vektor penghindaran: arah menjauhi titik obstacle terdekat
                escape_angle = math.atan2(py - nearest_pt[1], px - nearest_pt[0])
                near_wall = bool(overall_min < self.safe_distance)

                # D. Publikasikan ke CustomWallSensor
                c_msg = CustomWallSensor()
                c_msg.min_distance = float(overall_min)
                c_msg.dist_arena = float(min_dist_arena)
                c_msg.dist_custom = float(min_dist_custom if min_dist_custom != float('inf') else -1.0)
                c_msg.nearest_x = float(nearest_pt[0])
                c_msg.nearest_y = float(nearest_pt[1])
                c_msg.escape_angle = float(escape_angle)
                c_msg.near_wall = near_wall
                c_msg.nearest_obstacle = nearest_type
                self.custom_sensor_pub.publish(c_msg)

                # E. Publikasikan juga ke format standar /wall_sensor
                w_msg = WallSensor()
                w_msg.dist_left = dist_left
                w_msg.dist_right = dist_right
                w_msg.dist_bottom = dist_bottom
                w_msg.dist_top = dist_top
                w_msg.near_wall = near_wall
                self.standard_sensor_pub.publish(w_msg)

            rate.sleep()


if __name__ == '__main__':
    try:
        node = CustomWallSensorNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
