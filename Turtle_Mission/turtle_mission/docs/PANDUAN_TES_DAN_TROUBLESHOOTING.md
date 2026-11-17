# Panduan Tes, Troubleshooting, dan Checklist Pengumpulan

## 1. Build

```bash
mkdir -p ~/catkin_ws/src
cp -r turtle_mission ~/catkin_ws/src/
chmod +x ~/catkin_ws/src/turtle_mission/scripts/*.py
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

## 2. Menjalankan dan menguji

### Level 1
```bash
# Terminal 1 (otomatis mulai)
roslaunch turtle_mission level1.launch

# atau mulai manual
roslaunch turtle_mission level1.launch auto_start:=false
rosservice call /start_mission "start: true"   # terminal 2

# Pantau status
rostopic echo /mission/status
rostopic echo /mission/goal
rostopic hz /mission/status       # harus sekitar 10 Hz

# Graf node/topic (untuk screenshot README)
rqt_graph
```

### Level 2
```bash
roslaunch turtle_mission level2.launch
rostopic echo /wall_sensor
```

### Level 3
```bash
roslaunch turtle_mission level3.launch
rostopic echo /hunter/score
```

## 3. Masalah umum

1. **`cannot launch node of type [turtle_mission/...]: can't locate node`**
   - Penyebab: script Python belum executable.
   - Solusi: `chmod +x ~/catkin_ws/src/turtle_mission/scripts/*.py`
2. **`[rospack] Error: package 'turtle_mission' not found`**
   - Penyebab: terminal belum memuat environment workspace.
   - Solusi: `source ~/catkin_ws/devel/setup.bash` (atau tambahkan ke `~/.bashrc`).
3. **`ModuleNotFoundError: No module named 'turtle_mission.msg'`**
   - Penyebab: custom msg/srv belum di-generate.
   - Solusi: `cd ~/catkin_ws && catkin_make && source devel/setup.bash`
4. **`ERROR: Service [/start_mission] is not available`**
   - Penyebab: service dipanggil sebelum `mission_manager` siap.
   - Solusi: pakai `rosservice call --wait /start_mission "start: true"` (sudah dipakai di `level1.launch`).

## 4. Checklist pengumpulan

- [ ] Semua script di `scripts/` sudah `chmod +x` dan `catkin_make` berhasil.
- [ ] `README.md` berisi screenshot `rqt_graph` dan link video demo.
- [ ] Video demo 1-2 menit menampilkan Level 1, Level 2, dan Level 3 (+ perubahan warna pena).
- [ ] Package dikumpulkan sebagai `.zip` atau GitHub sesuai instruksi dosen.
