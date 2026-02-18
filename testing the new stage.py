import Tkinter as tk
import sys
import os
import atexit
import time
import socket
import json


sys.path.append(r"C:\Users\Localadmin_adeizaan\Desktop\Test_bench\IDEASTestbench_V1_6_4_1\scripts\GDS-100")
from tb_product import *
from math import *


# FIX for IDEAS
if not hasattr(sys, 'argv'):
    sys.argv = ['']

from zaber_client_py2 import ZaberClient
stage = ZaberClient()


class XYStepper:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER - X-LSM100 (Server Mode)")

        # --- TCP Stage Client ---
        self.stage = ZaberClient("127.0.0.1", 9999)

        # Parameters
        self.max_travel = 100.0
        self.speed = 10.0

        self.cx = 0.0
        self.cy = 0.0
        self.stop_requested = False
        self.paused = False
        self.pending_action = None
        self.detection_time = 30
        self.increment_time = False
        self.grid_size = 2
        self.decay_constant = log(2) / (4 * 60)
        self.direction_at_resume = 0

        try:
            print("Connecting to Zaber Server...")
            self.stage.connect("COM3")
            self.stage.home()
            print("Connected to Zaber server successfully.")
        except Exception as e:
            print("ERROR: Cannot connect to Zaber server:", e)

        self.init_ui()
        atexit.register(self.disconnect)

    # ==========================================================
    # UI
    # ==========================================================

    def init_ui(self):
        tk.Button(self.root, text="Home Stages", command=self.home_stages).grid(row=5, column=1)
        tk.Button(self.root, text="Disconnect", command=self.disconnect).grid(row=5, column=4)
        tk.Button(self.root, text="Start Snake Movement", command=self.start_movement).grid(row=12, column=1)
        tk.Button(self.root, text="Stop Movement", command=self.stop_movement).grid(row=12, column=4)
        tk.Button(self.root, text="Play", command=self.play).grid(row=9, column=6)

        tk.Label(self.root, text="Enter a value for x (mm):").grid(row=10, column=0)
        self.entry_cx = tk.Entry(self.root)
        self.entry_cx.insert(0, "0")
        self.entry_cx.grid(row=10, column=1)

        tk.Label(self.root, text="Enter a value for y (mm):").grid(row=10, column=4)
        self.entry_cy = tk.Entry(self.root)
        self.entry_cy.insert(0, "0")
        self.entry_cy.grid(row=10, column=5)

        tk.Button(self.root, text="Go to this position (x,y)", command=self.move_to_position).grid(row=11, column=1)

        tk.Label(self.root, text="Current X (mm):").grid(row=13, column=0)
        self.x_pos = tk.Label(self.root, text="0")
        self.x_pos.grid(row=13, column=1)

        tk.Label(self.root, text="Current Y (mm):").grid(row=13, column=3)
        self.y_pos = tk.Label(self.root, text="0")
        self.y_pos.grid(row=13, column=4)

        self.status_label = tk.Label(self.root, text="Status: Connected", fg="green")
        self.status_label.grid(row=14, column=1, columnspan=4)

    # ==========================================================
    # Stage Control via TCP
    # ==========================================================

    def move_to_position(self):
        self.status_label.config(text="Moving...", fg="orange")

        self.cx = float(self.entry_cx.get())
        self.cy = float(self.entry_cy.get())

        response = self.stage.move_absolute(self.cx, self.cy)

        if response["status"] == "success":
            self.cx = response["x"]
            self.cy = response["y"]

        self.x_pos.config(text="{:.3f}".format(self.cx))
        self.y_pos.config(text="{:.3f}".format(self.cy))
        self.status_label.config(text="Position reached", fg="green")

    def home_stages(self):
        self.status_label.config(text="Homing...", fg="orange")
        self.stage.home()

        pos = self.stage.get_position()
        self.cx = pos["x"]
        self.cy = pos["y"]

        self.x_pos.config(text="{:.3f}".format(self.cx))
        self.y_pos.config(text="{:.3f}".format(self.cy))
        self.status_label.config(text="Homing complete", fg="green")

    def stop_movement(self):
        self.stage.stop()
        self.stop_requested = True
        self.status_label.config(text="Stopped", fg="red")

    def disconnect(self):
        try:
            self.stage.disconnect()
        except:
            pass
        self.status_label.config(text="Disconnected", fg="red")

    # ==========================================================
    # Snake Pattern Logic (unchanged logic)
    # ==========================================================

    def move_1mm_x(self, reverse=False):
        x_val = self.cx - 1.0 if reverse else self.cx + 1.0
        response = self.stage.move_absolute(x_val, self.cy)
        if response["status"] == "success":
            self.cx = response["x"]
        self.x_pos.config(text="{:.3f}".format(self.cx))

    def move_1mm_y(self):
        y_val = self.cy + 1.0
        response = self.stage.move_absolute(self.cx, y_val)
        if response["status"] == "success":
            self.cy = response["y"]
        self.y_pos.config(text="{:.3f}".format(self.cy))

    def start_movement(self):
        self.stop_requested = False
        self.status_label.config(text="Starting scan...", fg="blue")
        self.root.after(2000, lambda: self.perform_step(0))

    def perform_step(self, direction):
        if self.stop_requested:
            return

        max_distance = self.grid_size

        if direction >= (max_distance + 1) ** 2:
            self.status_label.config(text="Scan complete", fg="green")
            return

        row = int(self.cy)

        if row % 2 == 0 and self.cx < max_distance:
            self.move_1mm_x()
        elif row % 2 != 0 and self.cx > 0:
            self.move_1mm_x(reverse=True)
        else:
            self.move_1mm_y()

        self.root.after(1000, lambda: self.perform_step(direction + 1))

    # ==========================================================
    # Detector (unchanged)
    # ==========================================================

    def log_data(self, x, y, duration):
        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        filename = 'logs/scan_x{:.3f}_y{:.3f}_{}.bin'.format(x, y, timestamp)

        if not os.path.exists('logs'):
            os.makedirs('logs')

        tb.newDataLogFile(filename)
        tb.enableDataLogging(True)
        time.sleep(duration)
        tb.enableDataLogging(False)

    def play(self):
        self.paused = False


if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()