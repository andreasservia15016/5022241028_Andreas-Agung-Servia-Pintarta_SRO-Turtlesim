#!/usr/bin/env python3
# ==============================================================================
# Node: hunter_gui.py
# Deskripsi:
# User Interface (GUI) berbasis Tkinter untuk misi Hunter (Level 3).
# Fitur:
# 1. Peta Mini Interaktif (2D Canvas): Menampilkan posisi real-time Hunter (turtle1)
#    dan Target. Klik pada area mana saja di peta untuk langsung spawn target di titik tersebut!
# 2. Input Manual Koordinat: Form input X dan Y (rentang 0.5 s/d 10.5).
# 3. Tombol Aksi: "Spawn di Koordinat" dan "Spawn Acak (Random)".
# 4. Mode Switcher: Pilih antara Mode Manual (UI Input) dan Mode Otomatis (Auto Random).
# 5. Live Dashboard: Menampilkan Skor, Jarak ke target, Waktu tempuh, dan status misi.
# Bebas dari karakter emoji Unicode untuk kompatibilitas penuh dengan X11 Render.
# ==============================================================================

import math
import tkinter as tk
from tkinter import ttk, messagebox
import rospy
from std_msgs.msg import String
from geometry_msgs.msg import Point
from turtlesim.msg import Pose
from turtle_mission.msg import Score


ARENA_SIZE = 11.08  # Batas arena default turtlesim (0.0 sampai 11.08)
CANVAS_SIZE = 280   # Ukuran kanvas mini-map dalam piksel


class HunterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Turtlesim Hunter - Control Panel")
        self.root.geometry("640x520")
        self.root.resizable(False, False)

        # Inisialisasi ROS Node
        rospy.init_node('hunter_gui', anonymous=True)

        # Publisher ke node hunter.py
        self.spawn_pub = rospy.Publisher('/hunter/spawn_coord', Point, queue_size=10)
        self.mode_pub = rospy.Publisher('/hunter/set_mode', String, queue_size=10)

        # State data
        self.hunter_pose = None
        self.target_pose = None
        self.current_score = 0
        self.elapsed_time = 0.0
        self.mode_var = tk.StringVar(value="manual")
        self.click_spawn_var = tk.BooleanVar(value=True)

        # Subscriber ROS
        rospy.Subscriber('/turtle1/pose', Pose, self.hunter_pose_cb)
        rospy.Subscriber('/hunter/target_pose', Pose, self.target_pose_cb)
        rospy.Subscriber('/hunter/score', Score, self.score_cb)

        # Bangun tampilan UI
        self.setup_ui()

        # Kirim mode awal ke hunter.py
        rospy.sleep(0.3)
        self.mode_pub.publish(self.mode_var.get())

        # Jadwalkan loop update berkala (50 ms = 20 FPS)
        self.root.after(50, self.update_loop)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def hunter_pose_cb(self, msg):
        self.hunter_pose = msg

    def target_pose_cb(self, msg):
        self.target_pose = msg

    def score_cb(self, msg):
        self.current_score = msg.score
        self.elapsed_time = msg.elapsed_time

    def setup_ui(self):
        # Gaya UI Modern & Bersih (Tanpa emoji untuk kompatibilitas X11)
        bg_main = "#f4f6f9"
        self.root.configure(bg=bg_main)

        # 1. HEADER FRAME
        header_frame = tk.Frame(self.root, bg="#1e272e", pady=8)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            header_frame,
            text="TURTLESIM HUNTER CONTROL PANEL",
            font=("Helvetica", 14, "bold"),
            fg="#00d2d3",
            bg="#1e272e"
        )
        title_lbl.pack()

        subtitle_lbl = tk.Label(
            header_frame,
            text="Pilih koordinat atau klik peta untuk memunculkan target perburuan",
            font=("Helvetica", 9),
            fg="#c8d6e5",
            bg="#1e272e"
        )
        subtitle_lbl.pack()

        # 2. MAIN CONTAINER
        main_frame = tk.Frame(self.root, bg=bg_main, padx=12, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- KOLOM KIRI: PETA INTERAKTIF 2D ---
        left_frame = tk.LabelFrame(
            main_frame,
            text=" Peta Arena (Klik untuk Spawn Target) ",
            font=("Helvetica", 10, "bold"),
            bg=bg_main,
            fg="#222f3e",
            padx=8,
            pady=8
        )
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.canvas = tk.Canvas(
            left_frame,
            width=CANVAS_SIZE,
            height=CANVAS_SIZE,
            bg="#2c3e50",
            highlightthickness=2,
            highlightbackground="#576574"
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Keterangan legenda peta
        legend_frame = tk.Frame(left_frame, bg=bg_main, pady=4)
        legend_frame.pack(fill=tk.X)

        tk.Label(legend_frame, text="[O] Hunter (turtle1)", fg="#2e86de", bg=bg_main, font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Label(legend_frame, text="[*] Target", fg="#ee5253", bg=bg_main, font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=4)

        click_chk = tk.Checkbutton(
            left_frame,
            text="Spawn otomatis saat klik peta",
            variable=self.click_spawn_var,
            bg=bg_main,
            font=("Helvetica", 8)
        )
        click_chk.pack(anchor="w")

        # --- KOLOM KANAN: FORM INPUT & KONTROL ---
        right_frame = tk.LabelFrame(
            main_frame,
            text=" Kontrol Lokasi Spawn ",
            font=("Helvetica", 10, "bold"),
            bg=bg_main,
            fg="#222f3e",
            padx=10,
            pady=8
        )
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Mode Selection
        mode_box = tk.LabelFrame(right_frame, text=" Mode Operasi ", bg=bg_main, font=("Helvetica", 9, "bold"))
        mode_box.pack(fill=tk.X, pady=(0, 8))

        rb_manual = tk.Radiobutton(
            mode_box,
            text="Mode Manual (Input UI)",
            variable=self.mode_var,
            value="manual",
            command=self.on_mode_change,
            bg=bg_main,
            font=("Helvetica", 9)
        )
        rb_manual.pack(anchor="w", padx=6, pady=2)

        rb_auto = tk.Radiobutton(
            mode_box,
            text="Mode Otomatis (Auto Random)",
            variable=self.mode_var,
            value="auto",
            command=self.on_mode_change,
            bg=bg_main,
            font=("Helvetica", 9)
        )
        rb_auto.pack(anchor="w", padx=6, pady=2)

        # Form Koordinat
        coord_box = tk.Frame(right_frame, bg=bg_main)
        coord_box.pack(fill=tk.X, pady=4)

        # Input X
        row_x = tk.Frame(coord_box, bg=bg_main)
        row_x.pack(fill=tk.X, pady=2)
        tk.Label(row_x, text="Koordinat X (0.5 - 10.5):", width=22, anchor="w", bg=bg_main, font=("Helvetica", 9)).pack(side=tk.LEFT)
        self.entry_x = tk.Entry(row_x, width=8, font=("Helvetica", 10, "bold"), justify="center")
        self.entry_x.insert(0, "7.50")
        self.entry_x.pack(side=tk.LEFT)

        # Input Y
        row_y = tk.Frame(coord_box, bg=bg_main)
        row_y.pack(fill=tk.X, pady=2)
        tk.Label(row_y, text="Koordinat Y (0.5 - 10.5):", width=22, anchor="w", bg=bg_main, font=("Helvetica", 9)).pack(side=tk.LEFT)
        self.entry_y = tk.Entry(row_y, width=8, font=("Helvetica", 10, "bold"), justify="center")
        self.entry_y.insert(0, "7.50")
        self.entry_y.pack(side=tk.LEFT)

        # Tombol Aksi Spawn
        btn_spawn = tk.Button(
            right_frame,
            text="SPAWN DI KOORDINAT",
            command=self.spawn_from_entries,
            bg="#10ac84",
            fg="white",
            font=("Helvetica", 10, "bold"),
            relief=tk.RAISED,
            pady=4
        )
        btn_spawn.pack(fill=tk.X, pady=(8, 4))

        btn_random = tk.Button(
            right_frame,
            text="SPAWN ACAK (RANDOM)",
            command=self.spawn_random,
            bg="#ee5253",
            fg="white",
            font=("Helvetica", 9, "bold"),
            relief=tk.RAISED,
            pady=3
        )
        btn_random.pack(fill=tk.X, pady=2)

        # Preset Cepat
        preset_box = tk.LabelFrame(right_frame, text=" Titik Preset Cepat ", bg=bg_main, font=("Helvetica", 8))
        preset_box.pack(fill=tk.X, pady=(8, 0))

        p_row1 = tk.Frame(preset_box, bg=bg_main)
        p_row1.pack(fill=tk.X, pady=2)
        tk.Button(p_row1, text="Kiri Bawah (2, 2)", font=("Helvetica", 8), command=lambda: self.set_preset(2.0, 2.0)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(p_row1, text="Kanan Bawah (9, 2)", font=("Helvetica", 8), command=lambda: self.set_preset(9.0, 2.0)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        p_row2 = tk.Frame(preset_box, bg=bg_main)
        p_row2.pack(fill=tk.X, pady=2)
        tk.Button(p_row2, text="Kanan Atas (9, 9)", font=("Helvetica", 8), command=lambda: self.set_preset(9.0, 9.0)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(p_row2, text="Kiri Atas (2, 9)", font=("Helvetica", 8), command=lambda: self.set_preset(2.0, 9.0)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # 3. DASHBOARD STATUS (FOOTER)
        footer_frame = tk.Frame(self.root, bg="#222f3e", pady=8, padx=12)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_score = tk.Label(
            footer_frame,
            text="SKOR: 0",
            font=("Helvetica", 13, "bold"),
            fg="#feca57",
            bg="#222f3e"
        )
        self.lbl_score.pack(side=tk.LEFT, padx=10)

        self.lbl_dist = tk.Label(
            footer_frame,
            text="Jarak Target: - m",
            font=("Helvetica", 10),
            fg="#c8d6e5",
            bg="#222f3e"
        )
        self.lbl_dist.pack(side=tk.LEFT, padx=15)

        self.lbl_status = tk.Label(
            footer_frame,
            text="Status: Siap",
            font=("Helvetica", 10, "italic"),
            fg="#1dd1a1",
            bg="#222f3e"
        )
        self.lbl_status.pack(side=tk.RIGHT, padx=10)

    def set_preset(self, x, y):
        self.entry_x.delete(0, tk.END)
        self.entry_x.insert(0, f"{x:.2f}")
        self.entry_y.delete(0, tk.END)
        self.entry_y.insert(0, f"{y:.2f}")
        if self.click_spawn_var.get():
            self.send_spawn(x, y)

    def on_canvas_click(self, event):
        # Konversi koordinat piksel kanvas ke koordinat dunia Turtlesim
        world_x = (event.x / CANVAS_SIZE) * ARENA_SIZE
        world_y = ((CANVAS_SIZE - event.y) / CANVAS_SIZE) * ARENA_SIZE

        world_x = max(0.5, min(10.5, world_x))
        world_y = max(0.5, min(10.5, world_y))

        self.entry_x.delete(0, tk.END)
        self.entry_x.insert(0, f"{world_x:.2f}")
        self.entry_y.delete(0, tk.END)
        self.entry_y.insert(0, f"{world_y:.2f}")

        if self.click_spawn_var.get():
            self.send_spawn(world_x, world_y)

    def spawn_from_entries(self):
        try:
            x = float(self.entry_x.get())
            y = float(self.entry_y.get())
            if not (0.5 <= x <= 10.5 and 0.5 <= y <= 10.5):
                messagebox.showwarning("Nilai Luar Batas", "Koordinat X dan Y harus berada di rentang 0.5 s/d 10.5 unit arena!")
                return
            self.send_spawn(x, y)
        except ValueError:
            messagebox.showerror("Format Salah", "Masukkan angka koordinat yang valid (contoh: 7.5)!")

    def spawn_random(self):
        p = Point()
        p.x = 0.0
        p.y = 0.0
        p.z = -1.0  # Sinyal spawn acak
        self.spawn_pub.publish(p)
        self.lbl_status.config(text="Status: Spawn target acak...")

    def send_spawn(self, x, y):
        p = Point()
        p.x = float(x)
        p.y = float(y)
        p.z = 0.0  # Sinyal spawn manual
        self.spawn_pub.publish(p)
        self.lbl_status.config(text=f"Status: Spawn di ({x:.2f}, {y:.2f})")

    def on_mode_change(self):
        selected_mode = self.mode_var.get()
        self.mode_pub.publish(selected_mode)
        if selected_mode == "auto":
            self.lbl_status.config(text="Status: Mode Otomatis Aktif")
        else:
            self.lbl_status.config(text="Status: Mode Manual (Klik untuk Spawn)")

    def update_loop(self):
        if rospy.is_shutdown():
            self.root.destroy()
            return

        # 1. Update gambar Kanvas 2D
        self.canvas.delete("all")

        # Gambar garis grid arena
        for i in range(1, int(ARENA_SIZE)):
            px = (i / ARENA_SIZE) * CANVAS_SIZE
            self.canvas.create_line(px, 0, px, CANVAS_SIZE, fill="#3d566e", dash=(2, 4))
            py = CANVAS_SIZE - (i / ARENA_SIZE) * CANVAS_SIZE
            self.canvas.create_line(0, py, CANVAS_SIZE, py, fill="#3d566e", dash=(2, 4))

        # Gambar Target jika ada
        if self.target_pose is not None:
            tx = (self.target_pose.x / ARENA_SIZE) * CANVAS_SIZE
            ty = CANVAS_SIZE - (self.target_pose.y / ARENA_SIZE) * CANVAS_SIZE
            r = 7
            self.canvas.create_oval(tx - r, ty - r, tx + r, ty + r, fill="#ff4757", outline="white", width=2)
            self.canvas.create_text(tx, ty - 12, text="TARGET", fill="#ff6b81", font=("Helvetica", 7, "bold"))

        # Gambar Hunter (turtle1)
        if self.hunter_pose is not None:
            hx = (self.hunter_pose.x / ARENA_SIZE) * CANVAS_SIZE
            hy = CANVAS_SIZE - (self.hunter_pose.y / ARENA_SIZE) * CANVAS_SIZE
            r = 8
            self.canvas.create_oval(hx - r, hy - r, hx + r, hy + r, fill="#2ed573", outline="white", width=2)

            # Indikator arah hadap (theta)
            heading_len = 16
            head_x = hx + heading_len * math.cos(self.hunter_pose.theta)
            head_y = hy - heading_len * math.sin(self.hunter_pose.theta)
            self.canvas.create_line(hx, hy, head_x, head_y, fill="#2ed573", width=3)
            self.canvas.create_text(hx, hy + 14, text="turtle1", fill="#7bed9f", font=("Helvetica", 7, "bold"))

        # 2. Update Label Skor dan Jarak
        self.lbl_score.config(text=f"SKOR: {self.current_score}")

        if self.hunter_pose is not None and self.target_pose is not None:
            dist = math.hypot(self.target_pose.x - self.hunter_pose.x, self.target_pose.y - self.hunter_pose.y)
            self.lbl_dist.config(text=f"Jarak Target: {dist:.2f} m")
            if dist < 0.5:
                self.lbl_status.config(text="Status: TARGET TERTANGKAP!")
            else:
                self.lbl_status.config(text="Status: Sedang Mengejar...")
        else:
            self.lbl_dist.config(text="Jarak Target: Menunggu...")

        self.root.after(50, self.update_loop)

    def on_close(self):
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = HunterGUI(root)
    root.mainloop()
