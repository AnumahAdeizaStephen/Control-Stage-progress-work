# aigrid_gui.py
# Python 2.7 (inside IDEAS)

from fileinput import filename
from math import exp, log
import sys
import Tkinter as tk
import time
import os
sys.path.append(
    r"C:\Users\Localadmin_adeizaan\Desktop\Test_bench\IDEASTestbench_V1_6_4_1\scripts\GDS-100")

from aigrid_client import StageClient
import tb_product

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
        self.grid_size = 4
        self.stop_requested = False
        self.paused = False
        self.pending_action = None
        self.detection_time = 30
        self.increment_time = False
        self.speed = 10.0
        # Decay constant for exponential compensation (half-life of 1 minute); 1 will be to 68 when gallium is been used.
        self.decay_constant = log(2) / (1 * 60) 
        self.snake_running = False
        self.max_steps = 100.0
        self.time_since_beginning = None
        self.direction_at_resume = 0

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
        if self.cx < 0 or self.cx > self.max_steps:
            self.update_status("X exceeds 100 mm limit", "red")
            return

        if self.cy < 0 or self.cy > self.max_steps:
            self.update_status("Y exceeds 100 mm limit", "red")
            return
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
        self.snake_running = True
        self.stop_requested = False
        self.paused = False
        self.pending_action = None

        self.time_since_beginning = time.time()
        self.direction_at_resume = 0

        self.update_status("Snake scan started", "blue")
        self.perform_step(0)

    def perform_step(self, step_index):

        if self.stop_requested:
            self.update_status("Stopped", "red")
            return

        if self.paused:
            self.pending_action = lambda: self.perform_step(step_index)
            return

        N = self.grid_size + 1
        max_steps = self.max_steps

        if step_index >= N * N:
            self.update_status("Scan complete", "green")
            self.snake_running = False
            return

        row = step_index // N
        col = step_index % N

        # Reverse direction on odd rows
        if row % 2 == 1:
            col = N - 1 - col

        start_x = float(self.entry_cx.get())
        start_y = float(self.entry_cy.get())

        target_x = start_x + col
        target_y = start_y + row

        if target_x < 0 or target_x > self.max_steps:
            self.update_status("X limit reached (100 mm)", "red")
            self.snake_running = False
            return

        if target_y < 0 or target_y > self.max_steps:
            self.update_status("Y limit reached (100 mm)", "red")
            self.snake_running = False
            return

        # Move stage using TCP client
        self.client.move_absolute(target_x, target_y)

        self.cx = target_x
        self.cy = target_y

        self.update_positions()

        self.root.after(500, lambda: self.start_detector(step_index))

    def stop_movement(self):
        self.snake_running = False
        self.stop_requested = True
        self.update_status("Stopped", "red")
        self.client.stop()

    def pause(self):
        self.paused = True
        print("Paused at X={:.3f}, Y={:.3f}".format(self.cx, self.cy))
        self.status_label.config(text="Status: Paused", fg="orange")

    def play(self):
        if self.paused and self.pending_action:
            print("Resuming after pause.")
            self.paused = False
            self.time_since_beginning = time.time()

            self.direction_at_resume = 0

            action = self.pending_action
            self.pending_action = None
            action()
        else:
            print("Play pressed, but not currently paused.")

    def start_detector(self, step_index):
        """Start detector at current position"""

        if self.paused:
            self.pending_action = lambda: self.start_detector(step_index)
            return

        if self.increment_time and self.time_since_beginning is not None:

            half_life = -1.0 / self.decay_constant * log(0.5)

            if time.time() - self.time_since_beginning > half_life:
                print("Auto-pause at step {} (x={}, y={})".format(
                    step_index, self.cx, self.cy))

                self.paused = True
                self.pending_action = lambda: self.start_detector(step_index)
                return

        x, y = self.cx, self.cy

        if self.increment_time:
            duration = self.increment_detection_time(
                self.decay_constant,
                self.detection_time,
                self.direction_at_resume
            )
        else:
            duration = self.detection_time

        self.direction_at_resume += 1

        self.log_data_nonblocking(x, y, duration, step_index)

    def log_data_nonblocking(self, x, y, duration, step_index):

        if not os.path.exists('logs'):
            os.makedirs('logs')

        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        filename = 'logs/scan_x{:.3f}_y{:.3f}_{}.bin'.format(x, y, timestamp)

        tb_product.tb.newDataLogFile(filename)
        tb_product.tb.enableDataLogging(True)

        print('Detector On.')
        print('Started data recording at (x={}, y={}).'.format(x, y))

        self.status_label.config(text="Status: Detector ON", fg="blue")

        self.root.after(int(duration * 1000),
                        lambda: self.finish_logging(x, y, step_index))

    def finish_logging(self, x, y, step_index):

        tb_product.tb.enableDataLogging(False)

        print('Stopped data recording at (x={}, y={})'.format(x, y))
        print('Detector Off.')

        self.status_label.config(text="Status: Detector OFF", fg="green")

        if self.snake_running and not self.stop_requested:
            self.root.after(500, lambda: self.perform_step(step_index + 1))

    def set_speed(self):
        self.client.set_speed(self.speed)
        self.update_status(
            "Speed set: {:.1f} mm/s".format(self.speed), "green")

    def disconnect(self):
        self.client.disconnect()
        self.update_status("Disconnected", "red")

    def increment_detection_time(self, lamda, tdet, i):
        """
        Exponential decay compensation.
        lamda: decay constant
        tdet: base detection time
        i: scan index
        """

        t0 = 0.0                      # time before scan starts
        td_0 = tdet + t0
        t_move = 24.0                 # movement time between points (seconds)

        t = t0
        td = td_0

        for k in range(1, i + 1):
            t = td + t_move
            td = (-1.0 / lamda) * log(
                exp(-lamda * t)
                + exp(-lamda * td_0)
                - exp(-lamda * t0)
            )

        return td - t


if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()
