# Turtle Mission – Sistem ROS 1 Turtlesim Otonom (Level 1 – Level 3 + Bonus)

Proyek ini mengimplementasikan sistem navigasi otonom pada simulator `turtlesim` menggunakan **ROS 1 Noetic** dan **Python 3 (`rospy`)** dengan pendekatan kontrol *closed-loop* (umpan balik `/turtle1/pose`).

## Level yang Diselesaikan
- [x] **Level 1 – Waypoint Patrol:** Navigasi berurutan ke daftar waypoint menggunakan P-Controller dengan toleransi `< 0.1` unit dan pemicu service `/start_mission`.
- [x] **Level 2 – Safe Explorer:** Eksplorasi arena secara acak menggunakan sensor jarak dinding virtual (`WallSensor.msg`) untuk menghindari tabrakan dengan dinding.
- [x] **Level 3 – Hunter:** Pemunculan target acak via `/spawn`, pengejaran otonom dengan P-Controller, eliminasi via `/kill` saat jarak `< 0.5`, serta publikasi skor ke `/hunter/score`.
- [x] **Bonus:** Perubahan warna pena `/turtle1/set_pen` secara otomatis pada setiap target baru di Level 3.

## Cara Build & Menjalankan

1. **Beri izin eksekusi dan build workspace:**
   ```bash
   chmod +x ~/catkin_ws/src/turtle_mission/scripts/*.py
   cd ~/catkin_ws
   catkin_make
   source devel/setup.bash
   ```

2. **Menjalankan Level 1 (Waypoint Patrol):**
   ```bash
   roslaunch turtle_mission level1.launch
   ```
   *(Jika ingin memanggil service secara manual, jalankan `roslaunch turtle_mission level1.launch auto_start:=false` lalu jalankan `rosservice call /start_mission "start: true"`)*

3. **Menjalankan Level 2 (Safe Explorer):**
   ```bash
   roslaunch turtle_mission level2.launch
   ```

4. **Menjalankan Level 3 (Hunter + Bonus):**
   ```bash
   roslaunch turtle_mission level3.launch
   ```

## Arsitektur Node, Topic, dan Service

| Komponen | Nama | Tipe | Keterangan |
| :--- | :--- | :--- | :--- |
| **Node** | `mission_manager` | Python Node | Mengelola urutan waypoint dari YAML & menyediakan service `/start_mission` |
| **Node** | `waypoint_controller` | Python Node | P-Controller *closed-loop* menuju waypoint & mempublikasikan status (10 Hz) |
| **Node** | `wall_sensor` | Python Node | Menghitung jarak `turtle1` ke 4 dinding arena (`0` – `11.08`) |
| **Node** | `safe_explorer` | Python Node | Menggerakkan `turtle1` menjelajah acak & berbelok menjauhi dinding |
| **Node** | `hunter` | Python Node | Melakukan `/spawn`, pengejaran P-Controller, `/kill`, dan `/set_pen` |
| **Topic** | `/mission/goal` | `geometry_msgs/Point` | Koordinat target waypoint aktif |
| **Topic** | `/mission/status` | `turtle_mission/MissionStatus` | Status progres misi (`IDLE`, `RUNNING`, `REACHED`, `FINISHED`) |
| **Topic** | `/wall_sensor` | `turtle_mission/WallSensor` | Jarak ke 4 dinding & flag bahaya `near_wall` |
| **Topic** | `/hunter/score` | `turtle_mission/Score` | Skor perburuan, nama target terakhir, & waktu tempuh |
| **Service** | `/start_mission` | `turtle_mission/StartMission` | Memulai eksekusi patroli waypoint pada Level 1 |

## Cara Mengubah Waypoint
Edit file `config/waypoints.yaml` tanpa perlu melakukan kompilasi ulang (`catkin_make`):
```yaml
waypoints:
  - [2.0, 2.0]
  - [9.0, 2.0]
  - [9.0, 9.0]
  - [2.0, 9.0]
return_to_start: true
```

## Dokumentasi Demo
- **Screenshot `rqt_graph`:** `[Lampirkan gambar rqt_graph di sini]`
- **Link Video Demo (1–2 menit):** `[Tempelkan tautan Google Drive / YouTube di sini]`
