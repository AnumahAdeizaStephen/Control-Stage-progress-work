# aigrid_gui.py
# Python 2.7 (inside IDEAS)
import sys
import Tkinter as tk
import time
import os



sys.path.append(r"C:\Users\Localadmin_adeizaan\Desktop\Test_bench\IDEASTestbench_V1_6_4_1\scripts\GDS-100")
from aigrid_client import StageClient
import tb_product

# FIX for IDEAS
if not hasattr(sys, 'argv'):
    sys.argv = ['']


class XYStepper:

    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID Controller")

        self.client = StageClient()

        self.cx = 0
        self.cy = 0
        self.grid_size = 2
        self.direction_index = 0
        self.stop_requested = False

        self.init_ui()

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def init_ui(self):

        tk.Button(self.root, text="Connect",
                  command=self.connect).grid(row=0, column=0)

        tk.Button(self.root, text="Home",
                  command=self.home).grid(row=0, column=1)

        tk.Button(self.root, text="Disconnect",
                  command=self.client.disconnect).grid(row=0, column=2)

        tk.Label(self.root, text="Detection time (s)").grid(row=1, column=0)
        self.entry_duration = tk.Entry(self.root)
        self.entry_duration.insert(0, "30")
        self.entry_duration.grid(row=1, column=1)

        tk.Button(self.root, text="Single Scan",
                  command=self.single_scan).grid(row=2, column=0)

        tk.Button(self.root, text="Start Snake",
                  command=self.start_snake).grid(row=3, column=0)

        tk.Button(self.root, text="Stop",
                  command=self.stop).grid(row=3, column=1)

        self.status = tk.Label(self.root, text="Idle", fg="blue")
        self.status.grid(row=4, column=0, columnspan=3)

    # ---------------------------------------------------------
    # Stage Control
    # ---------------------------------------------------------

    def connect(self):
        r = self.client.connect("COM3")
        self.status.config(text=str(r), fg="green")

    def home(self):
        self.client.home()
        self.status.config(text="Homed", fg="green")

    # ---------------------------------------------------------
    # Detector Logging
    # ---------------------------------------------------------

    def log_data(self, x, y, duration):
        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")

        if not os.path.exists("logs"):
            os.makedirs("logs")

        filename = "logs/scan_x%.3f_y%.3f_%s.bin" % (x, y, timestamp)

        tb_product.createLogFile(filename)
        time.sleep(duration)
        tb_product.tb.enableDataLogging(False)

    # ---------------------------------------------------------
    # Scan Logic
    # ---------------------------------------------------------

    def single_scan(self):
        duration = float(self.entry_duration.get())
        self.log_data(self.cx, self.cy, duration)
        self.status.config(text="Single scan complete", fg="green")

    def start_snake(self):
        self.stop_requested = False
        self.cx = 0
        self.cy = 0
        self.perform_step()

    def perform_step(self):

        if self.stop_requested:
            self.status.config(text="Stopped", fg="red")
            return

        self.client.move_absolute(self.cx, self.cy)

        duration = float(self.entry_duration.get())
        self.log_data(self.cx, self.cy, duration)

        if self.cy > self.grid_size:
            self.status.config(text="Scan Complete", fg="green")
            return

        if self.cy % 2 == 0:
            if self.cx < self.grid_size:
                self.cx += 1
            else:
                self.cy += 1
        else:
            if self.cx > 0:
                self.cx -= 1
            else:
                self.cy += 1

        self.root.after(500, self.perform_step)

    def stop(self):
        self.stop_requested = True
        self.client.stop()


if __name__ == "__main__":
    root = tk.Tk()
    XYStepper(root)
    root.mainloop()
