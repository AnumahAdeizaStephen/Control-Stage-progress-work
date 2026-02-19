# aigrid_gui.py
# Python 2.7 (inside IDEAS)

import tb_product
from aigrid_client import StageClient
from fileinput import filename
import sys
import Tkinter as tk
import time
import os
sys.path.append(
    r"C:\Users\Localadmin_adeizaan\Desktop\Test_bench\IDEASTestbench_V1_6_4_1\scripts\GDS-100")


# Ensure sys.argv exists for IDEAS
if not hasattr(sys, 'argv'):
    sys.argv = ['']


class XYStepper:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER - X-LSM100")

        # Stage client
        self.client = StageClient()

        # Stage & scan variables
        self.cx = 0
        self.cy = 0
        self.grid_size = 2
        self.stop_requested = False
        self.paused = False
        self.pending_action = None
        self.detection_time = 30
        self.increment_time = False
        self.speed = 10.0
        self.decay_constant = 1.0  # Used if incrementing detection time

        # Build the UI
        self.init_ui()

        # Initialize stage positions
        self.update_positions()

    # -----------------------
    # UI Layout
    # -----------------------
    def init_ui(self):
        padx = 5
        pady = 5

        # ----------- Row 0: Connection & Home -----------
        tk.Button(self.root, text="Connect", width=15,
                  command=self.connect_stages).grid(row=0, column=1, padx=padx, pady=pady)

        tk.Button(self.root, text="Home Stages", width=15,
                  command=self.home_stages).grid(row=0, column=0, padx=padx, pady=pady)
        tk.Button(self.root, text="Disconnect", width=15,
                  command=self.disconnect).grid(row=0, column=3, padx=padx, pady=pady)

        # ----------- Row 1: Stage speed -----------
        tk.Label(self.root, text="Stage speed (mm/s):").grid(row=1,
                                                             column=0, padx=padx, pady=pady)
        self.entry_speed = tk.Entry(self.root, width=10)
        self.entry_speed.insert(0, str(self.speed))
        self.entry_speed.grid(row=1, column=1, padx=padx, pady=pady)
        tk.Button(self.root, text="Set Speed", command=self.set_speed).grid(
            row=1, column=2, padx=padx, pady=pady)

        # ----------- Row 2: Detection time -----------
        tk.Label(self.root, text="Detection time (s):").grid(
            row=2, column=0, padx=padx, pady=pady)
        self.entry_duration = tk.Entry(self.root, width=10)
        self.entry_duration.insert(0, str(self.detection_time))
        self.entry_duration.grid(row=2, column=1, padx=padx, pady=pady)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(
            self.entry_duration)).grid(row=2, column=2, padx=padx, pady=pady)

        tk.Label(self.root, text="Increment detection time (1=Yes,0=No)").grid(
            row=2, column=3, padx=padx, pady=pady)
        self.increment_entry = tk.Entry(self.root, width=5)
        self.increment_entry.insert(0, "0")
        self.increment_entry.grid(row=2, column=4, padx=padx, pady=pady)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(
            self.increment_entry)).grid(row=2, column=5, padx=padx, pady=pady)

        # ----------- Row 3-4: X/Y entries and Go button -----------
        tk.Label(self.root, text="Enter X (mm):").grid(
            row=3, column=0, padx=padx, pady=pady)
        self.entry_cx = tk.Entry(self.root, width=10)
        self.entry_cx.insert(0, "0")
        self.entry_cx.grid(row=3, column=1, padx=padx, pady=pady)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(
            self.entry_cx)).grid(row=3, column=2, padx=padx, pady=pady)

        tk.Label(self.root, text="Enter Y (mm):").grid(
            row=3, column=3, padx=padx, pady=pady)
        self.entry_cy = tk.Entry(self.root, width=10)
        self.entry_cy.insert(0, "0")
        self.entry_cy.grid(row=3, column=4, padx=padx, pady=pady)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(
            self.entry_cy)).grid(row=3, column=5, padx=padx, pady=pady)

        tk.Button(self.root, text="Go to this position (x,y)", width=25, command=self.move_to_position).grid(
            row=4, column=0, columnspan=3, padx=padx, pady=pady)
        tk.Button(self.root, text="Launch single scan at (x,y)", width=25, command=self.run_detection_only).grid(
            row=4, column=3, columnspan=3, padx=padx, pady=pady)

        # ----------- Row 5: Snake movement -----------
        tk.Button(self.root, text="Start Snake Movement", width=25, command=self.start_movement).grid(
            row=5, column=0, columnspan=3, padx=padx, pady=pady)
        tk.Button(self.root, text="Stop Movement", width=25, command=self.stop_movement).grid(
            row=5, column=3, columnspan=3, padx=padx, pady=pady)

        # ----------- Row 6: Play/Pause -----------
        tk.Button(self.root, text="Play", width=10, command=self.play).grid(
            row=6, column=0, padx=padx, pady=pady)
        tk.Button(self.root, text="Pause", width=10, command=self.pause).grid(
            row=6, column=1, padx=padx, pady=pady)

        # ----------- Row 7: Current X/Y display -----------
        tk.Label(self.root, text="Current X (mm):").grid(
            row=7, column=0, padx=padx, pady=pady)
        self.x_pos = tk.Label(self.root, text="0")
        self.x_pos.grid(row=7, column=1, padx=padx, pady=pady)

        tk.Label(self.root, text="Current Y (mm):").grid(
            row=7, column=3, padx=padx, pady=pady)
        self.y_pos = tk.Label(self.root, text="0")
        self.y_pos.grid(row=7, column=4, padx=padx, pady=pady)

        # ----------- Row 8: Status label -----------
        self.status_label = tk.Label(self.root, text="Status: Idle", fg="blue")
        self.status_label.grid(row=8, column=0, columnspan=6, pady=pady)

    # -----------------------
    # Helper functions
    # -----------------------
    def save_value(self, entry_widget):
        try:
            val = float(entry_widget.get())
        except:
            self.update_status("Invalid number", "red")
            return

        if entry_widget == self.entry_cx:
            self.cx = val
        elif entry_widget == self.entry_cy:
            self.cy = val
        elif entry_widget == self.entry_duration:
            self.detection_time = val
        elif entry_widget == self.increment_entry:
            self.increment_time = (val == 1)
        elif entry_widget == self.entry_speed:
            self.speed = val
            self.set_speed()

        self.update_status("Value saved", "green")

    def update_status(self, message, color="blue"):
        self.status_label.config(text="Status: " + message, fg=color)
        self.root.update_idletasks()

    def update_positions(self):
        self.x_pos.config(text="{:.3f}".format(self.cx))
        self.y_pos.config(text="{:.3f}".format(self.cy))
        self.root.update_idletasks()

    # -----------------------
    # Stage control functions
    # -----------------------
    def connect_stages(self):
        response = self.client.connect("COM3")
        self.update_status("Connected", "green")
        print(response)

    def home_stages(self):
        self.update_status("Homing...", "orange")
        self.client.home()
        self.cx, self.cy = 0, 0
        self.update_positions()
        self.update_status("Homed", "green")

    def move_to_position(self):
        self.update_status("Moving...", "orange")
        self.client.move_absolute(self.cx, self.cy)
        self.update_positions()
        self.update_status("Position reached", "green")

    def run_detection_only(self):
        self.update_status("Running detector...", "blue")

        x, y = self.cx, self.cy
        duration = self.detection_time

        self.log_data_nonblocking(x, y, duration, 0)

        self.update_status("Single scan running", "green")

    def start_movement(self):
        self.stop_requested = False
        self.paused = False
        self.pending_action = None
        self.update_status("Snake scan started", "blue")
        self.perform_step(0)

    def perform_step(self, step_index):
        """Perform one step in snake pattern"""
        if self.stop_requested:
            self.status_label.config(text="Status: Stopped", fg="red")
            return

        if self.paused:
            self.pending_action = lambda: self.perform_step(step_index)
            return

        max_distance = self.grid_size
        row = int(self.cy)

        # Snake pattern: even rows → right, odd rows → left
        if row % 2 == 0:
            if self.cx < max_distance:
                self.cx += 1
            elif self.cy < max_distance:
                self.cy += 1
        else:
            if self.cx > 0:
                self.cx -= 1
            elif self.cy < max_distance:
                self.cy += 1
            else:
                self.status_label.config(
                    text="Status: Scan complete", fg="green")
                return

        # Move stage
        self.client.move_absolute(self.cx, self.cy)

        self.update_positions()

        # Start detector for this step
        self.root.after(500, lambda: self.start_detector(step_index))

    def stop_movement(self):
        self.stop_requested = True
        self.update_status("Stopped", "red")
        self.client.stop()

    def pause(self):
        self.paused = True
        print("Paused at X={:.3f}, Y={:.3f}".format(self.cx, self.cy))
        self.status_label.config(text="Status: Paused", fg="orange")

    def play(self):
        if self.paused and self.pending_action:
            self.paused = False
            action = self.pending_action
            self.pending_action = None
            print("Resuming scan...")
            action()

    def start_detector(self, step_index):
        """Start detector at current position"""
        if self.paused:
            self.pending_action = lambda: self.start_detector(step_index)
            return

        x, y = self.cx, self.cy
        duration = self.detection_time

        if self.increment_time:
            duration = self.increment_detection_time(
                self.decay_constant, self.detection_time, step_index)

        self.log_data_nonblocking(x, y, duration, step_index)

    def log_data_nonblocking(self, x, y, duration, step_index):

        if not os.path.exists('logs'):
            os.makedirs('logs')

        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        filename = 'logs/scan_x{:.3f}_y{:.3f}_{}.bin'.format(x, y, timestamp)

        # EXACT same flow as original working code
        tb_product.tb.newDataLogFile(filename)
        tb_product.tb.enableDataLogging(True)

        print('Detector On.')
        print('Started data recording at (x={}, y={}).'.format(x, y))

        self.status_label.config(text="Status: Detector ON", fg="blue")

        # Schedule stop after duration
        self.root.after(int(duration * 1000),
                        lambda: self.finish_logging(x, y, step_index))

    def finish_logging(self, x, y, step_index):

        tb_product.tb.enableDataLogging(False)

        print('Stopped data recording at (x={}, y={})'.format(x, y))
        print('Detector Off.')

        self.status_label.config(text="Status: Detector OFF", fg="green")

        # Continue snake only if not single scan
        if not self.stop_requested:
            self.root.after(500, lambda: self.perform_step(step_index))

    def set_speed(self):
        self.client.set_speed(self.speed)
        self.update_status(
            "Speed set: {:.1f} mm/s".format(self.speed), "green")

    def disconnect(self):
        self.client.disconnect()
        self.update_status("Disconnected", "red")

    def increment_detection_time(self, decay_constant, base_time, step_index):
        """Optional logic to increase detection time per step"""
        return base_time + decay_constant * step_index


if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()
