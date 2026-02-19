from math import *
from tb_product import *
import Tkinter as tk  # Import Tkinter for GUI
import sys  # Import sys module to access system-specific parameters and functions
import os  # Import os module for operating system related functions
import atexit  # Import atexit to handle cleanup on program exit
import time  # Import time module for timestamp and sleep functions

# Import X-LSM100 library (adjust based on your specific library)
try:
    from zaber_motion import Library, Units
    from zaber_motion.ascii import Connection, Axis
    LIBRARY_TYPE = "zaber"
except ImportError:
    try:
        # Alternative: if using pySerial direct control
        import serial
        LIBRARY_TYPE = "serial"
    except ImportError:
        raise ImportError(
            "Please install zaber-motion library: pip install zaber-motion")

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')


# Ensure sys.argv is available
if not hasattr(sys, 'argv'):
    sys.argv = ['']

'''
Modified for X-LSM 100 linear stage system.
You have to click on all of the 3 Save buttons to save the values in the tk.Entry before running "Go to this position 
(x,y)", "Launch a single scan by the detector at (x,y)" and "Start Snake Movement" buttons.
'''


class XYStepper:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER - X-LSM100")
        self.output = None

        # X-LSM100 specific parameters (adjust based on your stage specs)
        self.mm_per_unit = 1.0  # X-LSM100 typically works in mm directly
        self.max_travel = 100.0  # X-LSM100 has 100mm travel range
        self.speed = 10.0  # Default speed in mm/s (adjust as needed)

        self.cx = 0  # Current X position in mm
        self.cy = 0  # Current Y position in mm
        self.stop_requested = False  # Flag to stop movement
        self.paused = False  # Flag to indicate if paused
        self.pending_action = None  # Store what to resume after pause
        self.detection_time = 30  # Default value of the detection time
        self.increment_time = False  # Flag to enable/disable increment for detection time
        self.grid_size = 2  # For the scan of a 26x26 grid (in mm)
        # For the Gallium 68, in seconds-1
        self.decay_constant = log(2) / (4 * 60)
        self.direction_at_resume = 0

        # Initialize stage connection variables
        self.connection = None
        self.x_axis = None
        self.y_axis = None

        try:
            self.connect_stages()  # Connect to X-LSM100 stages
            self.init_ui()  # Initialize the user interface
        except Exception as e:
            print("Error connecting to X-LSM100 stages: {}".format(e))
            self.cleanup_stages()

        # Register the cleanup function to be called on program exit
        atexit.register(self.cleanup_stages)

    def connect_stages(self):
        """Connect to X-LSM100 stages using Zaber Motion Library"""
        if LIBRARY_TYPE == "zaber":
            Library.enable_device_db_store()
            # Adjust COM port as needed (use Device Manager to find correct port)
            self.connection = Connection.open_serial_port("COM3")

            # Get device list
            device_list = self.connection.detect_devices()
            print("Found {} device(s)".format(len(device_list)))

            if len(device_list) < 2:
                raise Exception(
                    "Expected 2 X-LSM100 stages (X and Y), found {}".format(len(device_list)))

            # Assign X and Y axes (adjust device numbers if needed)
            self.x_axis = device_list[0].get_axis(1)
            self.y_axis = device_list[1].get_axis(1)

            # Home the axes for accurate positioning
            print("Homing X axis...")
            self.x_axis.home()
            print("Homing Y axis...")
            self.y_axis.home()

            # Set movement speed
            self.x_axis.settings.set(
                "maxspeed", self.speed, Units.VELOCITY_MILLIMETRES_PER_SECOND)
            self.y_axis.settings.set(
                "maxspeed", self.speed, Units.VELOCITY_MILLIMETRES_PER_SECOND)

            print("X-LSM100 stages connected and homed successfully")

        elif LIBRARY_TYPE == "serial":
            # Fallback to direct serial control (you'll need to implement X-LSM100 protocol)
            self.connection = serial.Serial('COM3', baudrate=115200, timeout=5)
            print("Connected via serial - implement X-LSM100 protocol commands")

    def cleanup_stages(self):
        """Cleanup stage connections on exit"""
        try:
            if LIBRARY_TYPE == "zaber" and self.connection:
                # Move to home position before closing
                if self.x_axis:
                    self.x_axis.move_absolute(
                        0, Units.LENGTH_MILLIMETRES, wait_until_idle=False)
                if self.y_axis:
                    self.y_axis.move_absolute(
                        0, Units.LENGTH_MILLIMETRES, wait_until_idle=False)
                self.connection.close()
                print("X-LSM100 stages disconnected")
            elif LIBRARY_TYPE == "serial" and self.connection:
                if self.connection.isOpen():
                    self.connection.close()
                    print("Serial connection closed")
        except Exception as e:
            print("Error during cleanup: {}".format(e))

    # To allow the entry parameter only when it is a number
    def validate_number(self, entry):
        return (entry == "" or entry.replace(".", "", 1).replace("-", "", 1).isdigit())

###########################################################################################################################
###########################################################################################################################

    def init_ui(self):
        # Initialize the user interface elements
        tk.Button(self.root, text="Home Stages",
                  command=self.home_stages).grid(row=5, column=1)
        tk.Button(self.root, text="Disconnect",
                  command=self.disconnect).grid(row=5, column=4)
        tk.Button(self.root, text="Start Snake Movement",
                  command=self.start_movement).grid(row=12, column=1)
        tk.Button(self.root, text="Stop Movement",
                  command=self.stop_movement).grid(row=12, column=4)
        tk.Button(self.root, text="Play", command=self.play).grid(
            row=9, column=6)    # Add Play button

        # Manual interface that allows the user to choose a position (x and y)
        tk.Label(self.root, text="Enter a value for x (mm):").grid(
            row=10, column=0)
        self.entry_cx = tk.Entry(self.root, validate="key", validatecommand=(
            self.root.register(self.validate_number), "%P"))
        self.entry_cx.insert(0, "0")  # Default value
        self.entry_cx.grid(row=10, column=1)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(
            self.entry_cx)).grid(row=10, column=2)

        tk.Label(self.root, text="Enter a value for y (mm):").grid(
            row=10, column=4)
        self.entry_cy = tk.Entry(self.root, validate="key", validatecommand=(
            self.root.register(self.validate_number), "%P"))
        self.entry_cy.insert(0, "0")  # Default value
        self.entry_cy.grid(row=10, column=5)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(
            self.entry_cy)).grid(row=10, column=6)

        # Button to move to the position entered via the entries above
        tk.Button(self.root, text="Go to this position (x,y)",
                  command=self.move_to_position).grid(row=11, column=1)

        # Choose the detection time
        tk.Label(self.root, text="Enter detection time (in seconds):").grid(
            row=9, column=0)
        self.entry_duration = tk.Entry(self.root, validate="key", validatecommand=(
            self.root.register(self.validate_number), "%P"))
        self.entry_duration.insert(0, "30")  # Default value
        self.entry_duration.grid(row=9, column=1)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(
            self.entry_duration)).grid(row=9, column=2)

        # Choose to enable, or not, the increment for the detection time entered
        tk.Label(self.root, text="Increment for the detection time (Yes=1, No=0)").grid(
            row=9, column=3)
        self.increment = tk.Entry(self.root, validate="key", validatecommand=(
            self.root.register(self.validate_number), "%P"))
        self.increment.grid(row=9, column=4)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(
            self.increment)).grid(row=9, column=5)

        # Speed control
        tk.Label(self.root, text="Stage speed (mm/s):").grid(row=6, column=0)
        self.entry_speed = tk.Entry(self.root, validate="key", validatecommand=(
            self.root.register(self.validate_number), "%P"))
        self.entry_speed.insert(0, str(self.speed))
        self.entry_speed.grid(row=6, column=1)
        tk.Button(self.root, text="Set Speed",
                  command=self.set_speed).grid(row=6, column=2)

        # Button to use the detector once
        tk.Button(self.root, text="Launch a single scan by the detector at (x,y)",
                  command=self.run_detection_only).grid(row=11, column=4)

        # Labels to display the current X and Y positions
        tk.Label(self.root, text="Current X (mm):").grid(row=13, column=0)
        self.x_pos = tk.Label(self.root, text="0")
        self.x_pos.grid(row=13, column=1)
        tk.Label(self.root, text="Current Y (mm):").grid(row=13, column=3)
        self.y_pos = tk.Label(self.root, text="0")
        self.y_pos.grid(row=13, column=4)

        # Status label
        self.status_label = tk.Label(
            self.root, text="Status: Connected", fg="green")
        self.status_label.grid(row=14, column=1, columnspan=4)

###########################################################################################################################
###########################################################################################################################

    def save_value(self, entry_widget):
        """Save values from entry widgets"""
        value = entry_widget.get()
        if value.replace(".", "", 1).replace("-", "", 1).isdigit():
            value_float = float(value)
            if entry_widget == self.entry_cx:
                if 0 <= value_float <= self.max_travel:
                    self.cx = value_float
                else:
                    print("X value must be between 0 and {} mm".format(
                        self.max_travel))
            elif entry_widget == self.entry_cy:
                if 0 <= value_float <= self.max_travel:
                    self.cy = value_float
                else:
                    print("Y value must be between 0 and {} mm".format(
                        self.max_travel))
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

    def set_speed(self):
        """Set movement speed for X-LSM100 stages"""
        speed_str = self.entry_speed.get()
        if speed_str.replace(".", "", 1).isdigit():
            self.speed = float(speed_str)
            if LIBRARY_TYPE == "zaber":
                self.x_axis.settings.set(
                    "maxspeed", self.speed, Units.VELOCITY_MILLIMETRES_PER_SECOND)
                self.y_axis.settings.set(
                    "maxspeed", self.speed, Units.VELOCITY_MILLIMETRES_PER_SECOND)
            print("Speed set to {} mm/s".format(self.speed))
        else:
            print("Invalid speed value")

    def move_to_position(self):
        """Move to specified position"""
        self.tb_enable_data_logging(False)  # Turn off the detector
        self.status_label.config(
            text="Status: Moving to position...", fg="orange")

        print("Moving to position: X={} mm, Y={} mm".format(self.cx, self.cy))

        if LIBRARY_TYPE == "zaber":
            # Move both axes simultaneously
            self.x_axis.move_absolute(
                self.cx, Units.LENGTH_MILLIMETRES, wait_until_idle=False)
            self.y_axis.move_absolute(
                self.cy, Units.LENGTH_MILLIMETRES, wait_until_idle=False)

            # Wait for both to complete
            self.x_axis.wait_until_idle()
            self.y_axis.wait_until_idle()

            # Update actual positions
            self.cx = self.x_axis.get_position(Units.LENGTH_MILLIMETRES)
            self.cy = self.y_axis.get_position(Units.LENGTH_MILLIMETRES)

        self.x_pos.config(text="{:.3f}".format(self.cx))
        self.y_pos.config(text="{:.3f}".format(self.cy))
        self.status_label.config(text="Status: Position reached", fg="green")
        print("Position reached: X={:.3f} mm, Y={:.3f} mm".format(
            self.cx, self.cy))

    def run_detection_only(self):
        x, y = self.cx, self.cy
        duration = self.detection_time
        self.log_data(x, y, duration)

    def start_movement(self):
        """Start snake pattern movement"""
        self.stop_requested = False
        self.paused = False
        self.pending_action = None
        self.time_since_beginning = time.time()
        print("Welcome to AI-GRID measurement, getting ready...")
        self.status_label.config(text="Status: Starting scan...", fg="blue")
        # 5 seconds delay before starting
        self.root.after(5000, lambda: self.start_detector(0))

    def perform_step(self, direction):
        """Perform one step in the snake pattern"""
        if self.stop_requested:
            print("Movement stopped by user.")
            self.status_label.config(text="Status: Stopped by user", fg="red")
            return

        if self.paused:
            print("Movement paused at step {}, coordinate ({:.3f}, {:.3f})".format(
                direction, self.cx, self.cy))
            self.status_label.config(text="Status: Paused", fg="orange")
            self.pending_action = lambda: self.perform_step(direction)
            return

        max_distance = self.grid_size  # in mm

        x_start = float(self.entry_cx.get())
        y_start = float(self.entry_cy.get())
        x_corr = self.cx - x_start
        y_corr = self.cy - y_start

        if direction == (self.grid_size + 1) * (self.grid_size + 1) - 1:
            print("Completed the entire grid movement.")
            self.status_label.config(text="Status: Scan complete", fg="green")
            return

        # Snake pattern logic (same as before but using mm directly)
        current_row = int(y_corr)

        # On even rows, move right
        if current_row % 2 == 0 and x_corr < max_distance:
            self.root.after(30000, lambda: self.start_detector(direction + 1))
            self.move_1mm_x()
            return
        # On odd rows, move left
        elif current_row % 2 != 0 and x_corr > 0:
            self.root.after(30000, lambda: self.start_detector(direction + 1))
            self.move_1mm_x(reverse=True)
            return
        # At the end of a row, move down
        elif y_corr < max_distance and (abs(x_corr) < 0.01 or abs(x_corr - max_distance) < 0.01):
            self.root.after(30000, lambda: self.start_detector(direction + 1))
            self.move_1mm_y()
            return

    def stop_movement(self):
        """Stop movement"""
        self.stop_requested = True
        self.paused = False
        self.pending_action = None
        if LIBRARY_TYPE == "zaber":
            self.x_axis.stop()
            self.y_axis.stop()
        self.status_label.config(text="Status: Stopped", fg="red")

    def move_1mm_x(self, reverse=False):
        """Move 1mm in X direction"""
        x_val = self.cx - 1.0 if reverse else self.cx + 1.0

        if LIBRARY_TYPE == "zaber":
            self.x_axis.move_absolute(x_val, Units.LENGTH_MILLIMETRES)
            self.cx = self.x_axis.get_position(Units.LENGTH_MILLIMETRES)
        else:
            self.cx = x_val

        self.x_pos.config(text="{:.3f}".format(self.cx))

    def move_1mm_y(self):
        """Move 1mm in Y direction"""
        y_val = self.cy + 1.0

        if LIBRARY_TYPE == "zaber":
            self.y_axis.move_absolute(y_val, Units.LENGTH_MILLIMETRES)
            self.cy = self.y_axis.get_position(Units.LENGTH_MILLIMETRES)
        else:
            self.cy = y_val

        self.y_pos.config(text="{:.3f}".format(self.cy))

    def home_stages(self):
        """Home both X and Y stages"""
        self.status_label.config(text="Status: Homing stages...", fg="orange")
        print("Homing X-LSM100 stages...")

        if LIBRARY_TYPE == "zaber":
            self.x_axis.home()
            self.y_axis.home()
            self.cx = self.x_axis.get_position(Units.LENGTH_MILLIMETRES)
            self.cy = self.y_axis.get_position(Units.LENGTH_MILLIMETRES)
        else:
            self.cx = 0
            self.cy = 0

        self.x_pos.config(text="{:.3f}".format(self.cx))
        self.y_pos.config(text="{:.3f}".format(self.cy))
        self.status_label.config(text="Status: Homing complete", fg="green")
        print("Homing complete")

    def disconnect(self):
        """Disconnect from stages"""
        self.cleanup_stages()
        self.status_label.config(text="Status: Disconnected", fg="red")

    def pause(self):
        """Pause movement"""
        self.paused = True
        print("Pause requested.")

    def play(self):
        """Resume movement after pause"""
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

    def log_data(self, x, y, duration):
        """Log detector data at (x, y) for given duration"""
        import tb_product as tb  # Ensure correct import

        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        if not os.path.exists("logs"):
            os.makedirs("logs")

        filename = "logs/scan_x{:.3f}_y{:.3f}_{}.bin".format(x, y, timestamp)

        tb.createLogFile(filename)  # Create new log
        tb.enableDataLogging(True)
        print("Detector ON at X={:.3f}, Y={:.3f} for {:.1f}s".format(
            x, y, duration))
        self.status_label.config(text="Status: Detector ON", fg="blue")

        # After duration, turn off detector
        self.root.after(int(duration*1000), lambda: self.finish_logging(x, y))

    def finish_logging(self, x, y):
        import tb_product as tb
        tb.enableDataLogging(False)
        print("Detector OFF at X={:.3f}, Y={:.3f}".format(x, y))
        self.status_label.config(text="Status: Detector OFF", fg="green")

    def start_detector(self, direction):
        """Start detector at current position"""
        # Automatic pause if increment_detection_time exceeds threshold
        if time.time() - self.time_since_beginning > -1/self.decay_constant * log(0.5) and self.increment_time == True:
            print(
                "Auto-pause at direction {} (x={:.3f}, y={:.3f})".format(direction, self.cx, self.cy))
            self.paused = True
            self.pending_action = lambda: self.start_detector(direction)
            return

        x = self.cx
        y = self.cy

        if self.increment_time == True:
            self.log_data(x, y, self.increment_detection_time(
                self.decay_constant, self.detection_time, self.direction_at_resume))
        else:
            self.log_data(x, y, self.detection_time)
        self.direction_at_resume = self.direction_at_resume + 1
        self.root.after(3000, lambda: self.perform_step(direction))

    def tb_enable_data_logging(self, enable):
        """Control detector logging"""
        tb.enableDataLogging(enable)
        if enable:
            print("Detector On.")
        else:
            print("Detector Off.")

    def increment_detection_time(self, lamda, td_0, i):
        """Increment detection time to compensate for source decay"""
        t = 0
        td = td_0
        t_move = 53
        s = td - t
        detection_times = [td - t]
        for k in range(1, i + 1):
            t = td + t_move
            td = (-1 / lamda) * \
                log(exp(-lamda * (k * t_move + s)) + exp(-lamda * td_0) - 1)
            detection_times.append(td - t)
            s = s + (td - t)
        return (td-t)


if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()
