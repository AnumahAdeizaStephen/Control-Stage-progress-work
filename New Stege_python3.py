import sys
import Tkinter as tk
import time
import json

sys.path.append(r"C:\Users\Localadmin_adeizaan\Desktop\Test_bench\IDEASTestbench_V1_6_4_1\scripts\GDS-100")
from aigrid_client import AIGRIDClient

if not hasattr(sys, 'argv'):
    sys.argv = [''] 
class XYStepper:

    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER - X-LSM100 (TCP)")

        self.client = AIGRIDClient()

        # State
        self.cx = 0
        self.cy = 0
        self.grid_size = 2
        self.detection_time = 30
        self.increment_time = False
        self.direction_index = 0
        self.stop_requested = False


        # ---- Build UI AFTER loading state ----
        self.init_ui()

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def init_ui(self):

        # Row 0
        tk.Button(self.root, text="Connect",
                  command=self.connect).grid(row=0, column=0)

        tk.Button(self.root, text="Home Stages",
                  command=self.home).grid(row=0, column=1)

        tk.Button(self.root, text="Disconnect",
                  command=self.client.disconnect).grid(row=0, column=2)

        # Speed
        tk.Label(self.root, text="Stage speed (mm/s):").grid(row=1, column=0)
        self.entry_speed = tk.Entry(self.root)
        self.entry_speed.insert(0, "10")
        self.entry_speed.grid(row=1, column=1)

        # Detection time
        tk.Label(self.root, text="Detection time (s):").grid(row=2, column=0)
        self.entry_duration = tk.Entry(self.root)
        self.entry_duration.insert(0, "30")
        self.entry_duration.grid(row=2, column=1)

        tk.Label(self.root, text="Increment (1=yes,0=no)").grid(row=2, column=2)
        self.entry_increment = tk.Entry(self.root)
        self.entry_increment.insert(0, "0")
        self.entry_increment.grid(row=2, column=3)

        # Manual X/Y
        tk.Label(self.root, text="X (mm)").grid(row=3, column=0)
        self.entry_x = tk.Entry(self.root)
        self.entry_x.insert(0, "0")
        self.entry_x.grid(row=3, column=1)

        tk.Label(self.root, text="Y (mm)").grid(row=3, column=2)
        self.entry_y = tk.Entry(self.root)
        self.entry_y.insert(0, "0")
        self.entry_y.grid(row=3, column=3)

        tk.Button(self.root, text="Go to (X,Y)",
                  command=self.move_absolute).grid(row=4, column=0)

        tk.Button(self.root, text="Launch Single Scan",
                  command=self.single_scan).grid(row=4, column=1)

        # Snake
        tk.Button(self.root, text="Start Snake Movement",
                  command=self.start_snake).grid(row=5, column=0)

        tk.Button(self.root, text="Stop Movement",
                  command=self.stop).grid(row=5, column=1)

        # Position display
        tk.Label(self.root, text="Current X:").grid(row=6, column=0)
        self.label_x = tk.Label(self.root, text="0")
        self.label_x.grid(row=6, column=1)

        tk.Label(self.root, text="Current Y:").grid(row=6, column=2)
        self.label_y = tk.Label(self.root, text="0")
        self.label_y.grid(row=6, column=3)

        # Status
        self.status = tk.Label(self.root, text="Idle", fg="blue")
        self.status.grid(row=7, column=0, columnspan=4)

    # ---------------------------------------------------------
    # Basic Controls
    # ---------------------------------------------------------

    def connect(self):
        r = self.client.connect("COM3")
        self.status.config(text=str(r), fg="green")

    def home(self):
        self.client.home()
        self.update_position()
        self.status.config(text="Homed", fg="green")

    def move_absolute(self):
        self.cx = float(self.entry_x.get())
        self.cy = float(self.entry_y.get())

        r = self.client.move_absolute(self.cx, self.cy)
        self.update_position()
        self.status.config(text="Moved", fg="green")

    def update_position(self):
        """
        Docstring for update_position
        
        :param self: Description
        """
        r = self.client.get_position()
        self.label_x.config(text="%.3f" % r["x"])
        self.label_y.config(text="%.3f" % r["y"])

    def single_scan(self):
        self.detection_time = float(self.entry_duration.get())
        self.client.log_data(self.cx, self.cy, self.detection_time)
        self.status.config(text="Single scan complete", fg="green")

    # ---------------------------------------------------------
    # Snake Logic
    # ---------------------------------------------------------

    def start_snake(self):
        self.stop_requested = False
        self.direction_index = 0
        self.cx = 0
        self.cy = 0
        self.status.config(text="Scanning...", fg="blue")
        self.perform_step()

    def perform_step(self):
        if self.stop_requested:
            self.status.config(text="Stopped", fg="red")
            return

        # Move
        self.client.move_absolute(self.cx, self.cy)
        self.update_position()

        # Detection time logic
        base_time = float(self.entry_duration.get())
        increment_flag = int(self.entry_increment.get())

        if increment_flag == 1:
            r = self.client.increment_time(base_time,
                                           self.direction_index)
            duration = r["duration"]
        else:
            duration = base_time

        self.client.log_data(self.cx, self.cy, duration)

        self.direction_index += 1

        # Snake pattern
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