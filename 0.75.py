import Tkinter as tk  # Import Tkinter for GUI
import serial  # Import pySerial for serial communication
import sys  # Import sys module to access system-specific parameters and functions
import os  # Import os module for operating system related functions
import atexit  # Import atexit to handle cleanup on program exit
import time  # Import time module for timestamp and sleep functions

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *  # Import tb_product module

from math import *

# Ensure sys.argv is available
if not hasattr(sys, 'argv'):
    sys.argv = ['']

'''
You have to click on all of the 3 Save buttons to save the values in the tk.Entry before running "Go to this position 
(x,y)", "Launch a single scan by the detector at (x,y)" and "Start Snake Movement" buttons.
'''

class XYStepper:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER")
        self.output = None
        self.steps_per_mm = int(6 / 0.5 * 1600)  # Calculate steps per mm for stepper motor
        self.steps_per_1mm = int(self.steps_per_mm * 1)  # Steps per 0.75mm
        self.cx = 0  # Current X position
        self.cy = 0  # Current Y position
        self.stop_requested = False  # Flag to stop movement
        self.paused = False  # Flag to indicate if paused
        self.pending_action = None  # Store what to resume after pause
        self.detection_time = 30  # Default value of the detection time
        self.increment_time = False  # Flag to enable/disable increment for detection time
        self.grid_size = 2  # For the scan of a 8x8 grid (0 to 7, which is 8 points)
        self.decay_constant = log(2) / (4 * 60)  # For the Gallium 68, in seconds-1
        self.direction_at_resume = 0

        self.a = None  # Initialize serial connection to None

        try:
            self.connect_serial()  # Connect to the serial port
            self.init_ui()  # Initialize the user interface
        except serial.SerialException as e:
            print("Error opening COM4: {}".format(e))
            self.cleanup_serial()  # Ensure serial port is closed if error occurs

        # Register the cleanup function to be called on program exit
        atexit.register(self.cleanup_serial)

    def connect_serial(self):
        self.a = serial.Serial('COM4', baudrate=9600, timeout=20)  # Open serial port
        self.a.flush()  # Flush any existing data in the serial buffer

    def cleanup_serial(self):
        if self.a and self.a.isOpen():  # Check if serial port is open
            self.a.close()  # Close the serial port
            print("Serial port closed")  # Print confirmation of port closure

    # To allow the entry parameter only when it is a number
    def validate_number(self, entry):
        return (entry == "" or entry.replace(".", "", 1).isdigit())

    def init_ui(self):
        # Initialize the user interface elements
        tk.Button(self.root, text="Connect", command=self.connect).grid(row=5, column=1)
        tk.Button(self.root, text="Disconnect", command=self.disconnect).grid(row=5, column=4)
        tk.Button(self.root, text="Start Snake Movement", command=self.start_movement).grid(row=12, column=1)
        tk.Button(self.root, text="Stop Movement", command=self.stop_movement).grid(row=12, column=4)
        tk.Button(self.root, text="Play", command=self.play).grid(row=9, column=6)  # Add Play button

        # Manual interface that allows the user to choose a position (x and y)
        tk.Label(self.root, text="Enter a value for x :").grid(row=10, column=0)
        self.entry_cx = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.entry_cx.insert(0, "0")  # Default value
        self.entry_cx.grid(row=10, column=1)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_cx)).grid(row=10, column=2)

        tk.Label(self.root, text="Enter a value for y :").grid(row=10, column=4)
        self.entry_cy = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.entry_cy.insert(0, "0")  # Default value
        self.entry_cy.grid(row=10, column=5)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_cy)).grid(row=10, column=6)

        # Button to move to the position entered via the entries above
        tk.Button(self.root, text="Go to this position (x,y)", command=self.move_to_position).grid(row=11, column=1)

        # Choose the detection time
        tk.Label(self.root, text="Enter detection time (in seconds):").grid(row=9, column=0)
        self.entry_duration = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.entry_duration.insert(0, "30")  # Default value
        self.entry_duration.grid(row=9, column=1)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_duration)).grid(row=9, column=2)

        # Choose to enable, or not, the increment for the detection time entered
        tk.Label(self.root, text="Increment for the detection time (Yes=1, No=0)").grid(row=9, column=3)
        self.increment = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.increment.grid(row=9, column=4)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.increment)).grid(row=9, column=5)

        # Button to use the detector once, for the detection time indicated (entry_duration)
        tk.Button(self.root, text="Launch a single scan by the detector at (x,y)", command=self.run_detection_only).grid(row=11, column=4)

        # Labels to display the current X and Y positions
        self.x_pos = tk.Label(self.root, text="0")  # Label to display current X position
        self.x_pos.grid(row=13, column=1)
        self.y_pos = tk.Label(self.root, text="0")  # Label to display current Y position
        self.y_pos.grid(row=13, column=4)

    def save_value(self, entry_widget):
        value = entry_widget.get()
        if value.replace(".", "", 1).isdigit():
            value_float = float(value)
            if entry_widget == self.entry_cx:
                self.cx = float(value_float * self.steps_per_1mm)
            elif entry_widget == self.entry_cy:
                self.cy = float(value_float * self.steps_per_1mm)
            elif entry_widget == self.entry_duration:
                self.detection_time = value_float
            elif entry_widget == self.increment:
                if value_float == 1:
                    self.increment_time = True
                    print("Increment for the detection time is enabled.")
                elif value_float == 0:
                    self.increment_time = False
                    print("Increment for the detection time is disabled.")
                else:
                    print("Invalid value for increment. Please enter 1 or 0.")
        else:
            print("Invalid number entered.")

    def move_to_position(self):
        self.tb_enable_data_logging(False)  # Turn off the detector
        coordinate = 'Cx{}y{}'.format(float(self.cx), float(self.cy))
        print("Moving to starting point: {}".format(coordinate))
        self.send_command(coordinate)
        self.x_pos.config(text=str(self.cx / self.steps_per_1mm))
        self.y_pos.config(text=str(self.cy / self.steps_per_1mm))

    def run_detection_only(self):
        duration = self.detection_time
        x = self.cx / self.steps_per_1mm
        y = self.cy / self.steps_per_1mm
        self.log_data(x, y, duration)

    def start_movement(self):
        self.stop_requested = False
        self.paused = False
        self.pending_action = None
        self.time_since_beginning = time.time()
        print("Welcome to AI-GRID measurement, getting ready...")
        self.root.after(3000, lambda: self.start_detector(0))  # 3 seconds delay before starting

    def perform_step(self, direction):
        if self.stop_requested:
            print("Movement stopped by user.")
            return

        if self.paused:
            print("Movement paused at step {}, coordinate ({}, {})".format(direction, self.cx, self.cy))
            self.pending_action = lambda: self.perform_step(direction)
            return

        total_points = (self.grid_size + 1) * (self.grid_size + 1)
        if direction >= total_points:
            print("Completed the entire grid movement.")
            return

        # Calculate current grid indices
        grid_x = direction % (self.grid_size + 1)
        grid_y = direction // (self.grid_size + 1)

        # For snake movement (zig-zag left/right)
        if grid_y % 2 == 0:
            actual_x = grid_x
        else:
            actual_x = self.grid_size - grid_x

        # Compute actual positions in steps
        new_cx = float(self.entry_cx.get()) * self.steps_per_1mm + actual_x * self.steps_per_1mm
        new_cy = float(self.entry_cy.get()) * self.steps_per_1mm + grid_y * self.steps_per_1mm

        # Move to the new position
        coordinate = 'Cx{}y{}'.format(new_cx, new_cy)
        self.send_command(coordinate)
        self.cx = new_cx
        self.cy = new_cy
        self.x_pos.config(text=str(self.cx / self.steps_per_1mm))
        self.y_pos.config(text=str(self.cy / self.steps_per_1mm))

        # After measuring, move to next step
        self.root.after(30000, lambda: self.start_detector(direction + 1))

    def stop_movement(self):
        self.stop_requested = True
        self.paused = False
        self.pending_action = None

    def connect(self):
        try:
            self.a.open()
            self.read_until_ready()
        except serial.SerialException as e:
            print("Error connecting to COM4: {}".format(e))
            self.cleanup_serial()

    def disconnect(self):
        try:
            self.send_command('Stop')
            self.a.close()
        except serial.SerialException as e:
            print("Error disconnecting from COM4: {}".format(e))
            self.cleanup_serial()

    def pause(self):
        self.paused = True
        print("Pause requested.")

    def play(self):
        if self.paused:
            print("Resuming after pause.")
            self.paused = False
            if self.pending_action:
                self.direction_at_resume = 0
                self.time_since_beginning = time.time()
                action = self.pending_action
                self.pending_action = None
                action()
        else:
            print("Play pressed, but not currently paused.")

    def send_command(self, command):
        try:
            print("Sending command: {}".format(command))  # Debug statement
            self.a.write('{}\n'.format(command).encode())
        except serial.SerialException as e:
            print("Error sending command: {}".format(e))
            self.cleanup_serial()

    def read_until_ready(self):
        try:
            while True:
                received = self.a.readline().strip()
                print("Received: {}".format(received))  # Debug statement
                if received == 'Ready':
                    break
        except serial.SerialException as e:
            print("Error reading from serial port: {}".format(e))
            self.cleanup_serial()

    def log_data(self, x, y, duration):
        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        filename = 'logs/scan_x{}_y{}_{}.bin'.format(x - float(self.entry_cx.get()), y - float(self.entry_cy.get()), timestamp)
        tb.newDataLogFile(filename)
        tb.enableDataLogging(True)
        print('Detector On.')
        print('Started data recording at (x={}, y={}).'.format(x, y))
        time.sleep(duration)
        tb.enableDataLogging(False)
        print('Stopped data recording at (x={}, y={})'.format(x, y))
        print('Detector Off.')

    def start_detector(self, direction):
        # Automatic pause if increment_detection_time exceeds threshold
        if time.time() - self.time_since_beginning > -1 / self.decay_constant * log(0.5) and self.increment_time == True:
            print("Auto-pause at direction {} (x={}, y={})".format(direction, self.cx, self.cy))
            self.paused = True
            self.pending_action = lambda: self.start_detector(direction)
            return

        x = self.cx / self.steps_per_1mm
        y = self.cy / self.steps_per_1mm

        if self.increment_time == True:
            self.log_data(x, y, self.increment_detection_time(self.decay_constant, self.detection_time, self.direction_at_resume))
        else:
            self.log_data(x, y, self.detection_time)
        self.direction_at_resume = self.direction_at_resume + 1
        self.root.after(3000, lambda: self.perform_step(direction))

    def tb_enable_data_logging(self, enable):
        tb.enableDataLogging(enable)
        if enable:
            print("Detector On.")
        else:
            print("Detector Off.")

    def increment_detection_time(self, lamda, td_0, i):  # i is the ith detection time
        t = 0
        td = td_0
        t_move = 53
        s = td - t
        detection_times = [td - t]
        for k in range(1, i + 1):
            t = td + t_move
            td = (-1 / lamda) * log(exp(-lamda * (k * t_move + s)) + exp(-lamda * td_0) - 1)
            detection_times.append(td - t)
            s = s + (td - t)
        return (td - t)

if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()