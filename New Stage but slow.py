import Tkinter as tk  # Import Tkinter for GUI
import sys  # Import sys module to access system-specific parameters and functions
import os  # Import os module for operating system related functions
import atexit  # Import atexit to handle cleanup on program exit
import time  # Import time module for timestamp and sleep functions
import subprocess  # Import subprocess to call Python 3 scripts
import json  # Import json for data exchange

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *  # Import tb_product module

from math import *

# Ensure sys.argv is available
if not hasattr(sys, 'argv'):
    sys.argv = ['']

'''
Modified for X-LSM 100 linear stage system using Python 2.7 with subprocess calls to Python 3.
This solution uses subprocess to call Python 3 scripts for each stage operation.

WARNING: This is NOT RECOMMENDED for production use due to:
- High latency (each call takes 1-2 seconds)
- Reliability issues
- Difficult debugging
- Resource overhead

SETUP INSTRUCTIONS:
1. Create the helper Python 3 scripts (see below)
2. Run this script: python xy_controller_xlsm100_py2_subprocess.py

Required Python 3 helper scripts in the same directory:
- zaber_connect.py
- zaber_move.py
- zaber_home.py
- zaber_get_position.py
- zaber_stop.py
- zaber_set_speed.py
- zaber_disconnect.py
'''

class ZaberSubprocessClient:
    """Client that uses subprocess to call Python 3 Zaber scripts"""
    
    def __init__(self, python3_path='python3'):
        """
        Initialize subprocess client
        
        Args:
            python3_path: Path to Python 3 executable (e.g., 'python3', 'py -3', or full path)
        """
        self.python3_path = python3_path
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
    def _run_python3_script(self, script_name, *args):
        """
        Run a Python 3 script and return JSON result
        
        Args:
            script_name: Name of the Python 3 script to run
            *args: Arguments to pass to the script
            
        Returns:
            dict: Parsed JSON response from the script
        """
        script_path = os.path.join(self.script_dir, script_name)
        
        # Build command
        if self.python3_path == 'py -3':
            cmd = ['py', '-3', script_path] + list(args)
        else:
            cmd = [self.python3_path, script_path] + list(args)
        
        try:
            # Run subprocess and capture output
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            result = json.loads(output.strip())
            return result
        except subprocess.CalledProcessError as e:
            return {
                'status': 'error',
                'message': 'Subprocess error: {}'.format(str(e))
            }
        except ValueError as e:
            return {
                'status': 'error',
                'message': 'JSON decode error: {}'.format(str(e))
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': 'Unexpected error: {}'.format(str(e))
            }
    
    def connect_stages(self, com_port='COM4'):
        """Connect to Zaber stages"""
        return self._run_python3_script('zaber_connect.py', com_port)
    
    def move_absolute(self, x, y):
        """Move to absolute position"""
        return self._run_python3_script('zaber_move.py', str(x), str(y))
    
    def get_position(self):
        """Get current position"""
        return self._run_python3_script('zaber_get_position.py')
    
    def home(self):
        """Home both axes"""
        return self._run_python3_script('zaber_home.py')
    
    def stop(self):
        """Stop movement"""
        return self._run_python3_script('zaber_stop.py')
    
    def set_speed(self, speed):
        """Set speed"""
        return self._run_python3_script('zaber_set_speed.py', str(speed))
    
    def disconnect_stages(self):
        """Disconnect from stages"""
        return self._run_python3_script('zaber_disconnect.py')


class XYStepper:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER - X-LSM100 (Subprocess)")
        self.output = None
        
        # X-LSM100 specific parameters
        self.mm_per_unit = 1.0  # X-LSM100 works directly in mm
        self.max_travel = 100.0  # X-LSM100 has 100mm travel range
        self.speed = 10.0  # Default speed in mm/s
        
        self.cx = 0  # Current X position in mm
        self.cy = 0  # Current Y position in mm
        self.stop_requested = False  # Flag to stop movement
        self.paused = False  # Flag to indicate if paused
        self.pending_action = None  # Store what to resume after pause
        self.detection_time = 30  # Default value of the detection time
        self.increment_time = False  # Flag to enable/disable increment for detection time
        self.grid_size = 2  # For the scan of a grid in mm
        self.decay_constant = log(2) / (4 * 60)  # For the Gallium 68, in seconds-1
        self.direction_at_resume = 0

        # Initialize subprocess client
        # Change 'python3' to 'py -3' on Windows or full path if needed
        self.zaber_client = ZaberSubprocessClient(python3_path='python3')

        try:
            self.connect_stages()  # Connect to X-LSM100 stages
            self.init_ui()  # Initialize the user interface
        except Exception as e:
            print("Error connecting to X-LSM100 stages: {}".format(e))
            self.cleanup_stages()

        # Register the cleanup function to be called on program exit
        atexit.register(self.cleanup_stages)

    def connect_stages(self):
        """Connect to X-LSM100 stages using subprocess calls"""
        try:
            print("Connecting to X-LSM100 stages via subprocess...")
            result = self.zaber_client.connect_stages('COM3')  # Change COM port as needed
            
            if result['status'] == 'success':
                print("Stage connection: {}".format(result['message']))
                # Get initial position after homing
                pos = self.zaber_client.get_position()
                if pos['status'] == 'success':
                    self.cx = pos['x']
                    self.cy = pos['y']
                    print("Initial position: X={:.3f} mm, Y={:.3f} mm".format(self.cx, self.cy))
            else:
                raise Exception("Failed to connect to stages: {}".format(result.get('message', 'Unknown error')))
                
        except Exception as e:
            print("Error in connect_stages: {}".format(e))
            raise

    def cleanup_stages(self):
        """Cleanup stage connections on exit"""
        try:
            print("Disconnecting from stages...")
            result = self.zaber_client.disconnect_stages()
            if result['status'] == 'success':
                print("X-LSM100 stages disconnected successfully")
        except Exception as e:
            print("Error during cleanup: {}".format(e))

    # To allow the entry parameter only when it is a number
    def validate_number(self, entry): 
        return(entry == "" or entry.replace(".", "", 1).replace("-", "", 1).isdigit())

###########################################################################################################################
###########################################################################################################################

    def init_ui(self):
        # Initialize the user interface elements
        tk.Button(self.root, text="Home Stages", command=self.home_stages).grid(row=5, column=1)
        tk.Button(self.root, text="Disconnect", command=self.disconnect).grid(row=5, column=4)
        tk.Button(self.root, text="Start Snake Movement", command=self.start_movement).grid(row=12, column=1)
        tk.Button(self.root, text="Stop Movement", command=self.stop_movement).grid(row=12, column=4)
        tk.Button(self.root, text="Play", command=self.play).grid(row=9, column=6)    # Add Play button

        # Manual interface that allows the user to choose a position (x and y)
        tk.Label(self.root, text="Enter a value for x (mm):").grid(row=10, column=0)
        self.entry_cx = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.entry_cx.insert(0, "0")  # Default value
        self.entry_cx.grid(row=10, column=1)
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_cx)).grid(row=10, column=2)

        tk.Label(self.root, text="Enter a value for y (mm):").grid(row=10, column=4)
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

        # Speed control
        tk.Label(self.root, text="Stage speed (mm/s):").grid(row=6, column=0)
        self.entry_speed = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.entry_speed.insert(0, str(self.speed))
        self.entry_speed.grid(row=6, column=1)
        tk.Button(self.root, text="Set Speed", command=self.set_speed).grid(row=6, column=2)

        # Button to use the detector once
        tk.Button(self.root, text="Launch a single scan by the detector at (x,y)", command=self.run_detection_only).grid(row=11, column=4) 
   
        # Labels to display the current X and Y positions
        tk.Label(self.root, text="Current X (mm):").grid(row=13, column=0)
        self.x_pos = tk.Label(self.root, text="0")
        self.x_pos.grid(row=13, column=1)
        tk.Label(self.root, text="Current Y (mm):").grid(row=13, column=3)
        self.y_pos = tk.Label(self.root, text="0")
        self.y_pos.grid(row=13, column=4)

        # Status label
        self.status_label = tk.Label(self.root, text="Status: Connected", fg="green")
        self.status_label.grid(row=14, column=1, columnspan=4)
        
        # Warning label
        warning_label = tk.Label(self.root, text="WARNING: Subprocess mode - expect slow performance", 
                                fg="red", font=("Arial", 10, "bold"))
        warning_label.grid(row=15, column=0, columnspan=6)

        # Update display with current positions
        self.x_pos.config(text="{:.3f}".format(self.cx))
        self.y_pos.config(text="{:.3f}".format(self.cy))

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
                    print("X value saved: {:.3f} mm".format(self.cx))
                else:
                    print("X value must be between 0 and {} mm".format(self.max_travel))
            elif entry_widget == self.entry_cy:
                if 0 <= value_float <= self.max_travel:
                    self.cy = value_float
                    print("Y value saved: {:.3f} mm".format(self.cy))
                else:
                    print("Y value must be between 0 and {} mm".format(self.max_travel))
            elif entry_widget == self.entry_duration:
                self.detection_time = value_float
                print("Detection time saved: {} seconds".format(self.detection_time))
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
            try:
                print("Setting speed to {} mm/s (this may take a moment)...".format(self.speed))
                result = self.zaber_client.set_speed(self.speed)
                if result['status'] == 'success':
                    print("Speed set to {} mm/s".format(self.speed))
                    self.status_label.config(text="Status: Speed updated", fg="green")
                else:
                    print("Error setting speed: {}".format(result.get('message', 'Unknown error')))
            except Exception as e:
                print("Error setting speed: {}".format(e))
        else:
            print("Invalid speed value")

    def move_to_position(self):
        """Move to specified position"""
        self.tb_enable_data_logging(False)  # Turn off the detector
        self.status_label.config(text="Status: Moving to position...", fg="orange")
        self.root.update()  # Force GUI update
        
        print("Moving to position: X={:.3f} mm, Y={:.3f} mm (this may take a moment)...".format(self.cx, self.cy))
        
        try:
            result = self.zaber_client.move_absolute(self.cx, self.cy)
            
            if result['status'] == 'success':
                # Update actual positions from the stage
                self.cx = result['x']
                self.cy = result['y']
                
                self.x_pos.config(text="{:.3f}".format(self.cx))
                self.y_pos.config(text="{:.3f}".format(self.cy))
                self.status_label.config(text="Status: Position reached", fg="green")
                print("Position reached: X={:.3f} mm, Y={:.3f} mm".format(self.cx, self.cy))
            else:
                print("Error moving to position: {}".format(result.get('message', 'Unknown error')))
                self.status_label.config(text="Status: Move failed", fg="red")
                
        except Exception as e:
            print("Exception during move: {}".format(e))
            self.status_label.config(text="Status: Error", fg="red")

    def run_detection_only(self):
        """Run detector at current position"""
        duration = self.detection_time
        x = self.cx
        y = self.cy
        self.log_data(x, y, duration)

    def start_movement(self):
        """Start snake pattern movement"""
        self.stop_requested = False
        self.paused = False
        self.pending_action = None
        self.time_since_beginning = time.time()
        print("Welcome to AI-GRID measurement, getting ready...")
        print("NOTE: Subprocess mode will be SLOWER than normal operation")
        self.status_label.config(text="Status: Starting scan...", fg="blue")
        self.root.after(5000, lambda: self.start_detector(0))  # 5 seconds delay before starting

    def perform_step(self, direction):
        """Perform one step in the snake pattern"""
        if self.stop_requested:
            print("Movement stopped by user.")
            self.status_label.config(text="Status: Stopped by user", fg="red")
            return

        if self.paused:
            print("Movement paused at step {}, coordinate ({:.3f}, {:.3f})".format(direction, self.cx, self.cy))
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
        
        # Snake pattern logic using mm directly
        current_row = int(round(y_corr))
        
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
        
        try:
            print("Stopping stage movement (this may take a moment)...")
            result = self.zaber_client.stop()
            if result['status'] == 'success':
                print("Stage movement stopped")
        except Exception as e:
            print("Error stopping movement: {}".format(e))
            
        self.status_label.config(text="Status: Stopped", fg="red")

    def move_1mm_x(self, reverse=False):
        """Move 1mm in X direction"""
        x_val = self.cx - 1.0 if reverse else self.cx + 1.0
        
        try:
            result = self.zaber_client.move_absolute(x_val, self.cy)
            if result['status'] == 'success':
                self.cx = result['x']
                self.cy = result['y']
                self.x_pos.config(text="{:.3f}".format(self.cx))
                print("Moved to X={:.3f} mm".format(self.cx))
            else:
                print("Error moving X: {}".format(result.get('message', 'Unknown error')))
        except Exception as e:
            print("Exception during X move: {}".format(e))

    def move_1mm_y(self):
        """Move 1mm in Y direction"""
        y_val = self.cy + 1.0
        
        try:
            result = self.zaber_client.move_absolute(self.cx, y_val)
            if result['status'] == 'success':
                self.cx = result['x']
                self.cy = result['y']
                self.y_pos.config(text="{:.3f}".format(self.cy))
                print("Moved to Y={:.3f} mm".format(self.cy))
            else:
                print("Error moving Y: {}".format(result.get('message', 'Unknown error')))
        except Exception as e:
            print("Exception during Y move: {}".format(e))

    def home_stages(self):
        """Home both X and Y stages"""
        self.status_label.config(text="Status: Homing stages...", fg="orange")
        self.root.update()  # Force GUI update
        print("Homing X-LSM100 stages (this may take a moment)...")
        
        try:
            result = self.zaber_client.home()
            if result['status'] == 'success':
                print("Homing complete: {}".format(result['message']))
                
                # Get position after homing
                pos = self.zaber_client.get_position()
                if pos['status'] == 'success':
                    self.cx = pos['x']
                    self.cy = pos['y']
                    
                    self.x_pos.config(text="{:.3f}".format(self.cx))
                    self.y_pos.config(text="{:.3f}".format(self.cy))
                    self.status_label.config(text="Status: Homing complete", fg="green")
                    print("Position after homing: X={:.3f} mm, Y={:.3f} mm".format(self.cx, self.cy))
            else:
                print("Error homing: {}".format(result.get('message', 'Unknown error')))
                self.status_label.config(text="Status: Homing failed", fg="red")
                
        except Exception as e:
            print("Exception during homing: {}".format(e))
            self.status_label.config(text="Status: Error", fg="red")

    def disconnect(self):
        """Disconnect from stages"""
        self.cleanup_stages()
        self.status_label.config(text="Status: Disconnected", fg="red")

    def pause(self):
        """Pause movement"""
        self.paused = True
        print("Pause requested.")
        self.status_label.config(text="Status: Paused", fg="orange")

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
                self.status_label.config(text="Status: Resuming...", fg="blue")
                action()
        else:
            print("Play pressed, but not currently paused.")

    def log_data(self, x, y, duration):
        """Log detector data"""
        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        x_offset = x - float(self.entry_cx.get())
        y_offset = y - float(self.entry_cy.get())
        filename = 'logs/scan_x{:.3f}_y{:.3f}_{}.bin'.format(x_offset, y_offset, timestamp)
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        tb.newDataLogFile(filename)
        tb.enableDataLogging(True)
        print('Detector On.')
        print('Started data recording at (x={:.3f}, y={:.3f}).'.format(x, y))
        time.sleep(duration) 
        tb.enableDataLogging(False)
        print('Stopped data recording at (x={:.3f}, y={:.3f})'.format(x, y))
        print('Detector Off.') 

    def start_detector(self, direction):
        """Start detector at current position"""
        # Automatic pause if increment_detection_time exceeds threshold
        if time.time() - self.time_since_beginning > -1/self.decay_constant * log(0.5) and self.increment_time==True:
            print("Auto-pause at direction {} (x={:.3f}, y={:.3f})".format(direction, self.cx, self.cy))
            self.paused = True
            self.pending_action = lambda: self.start_detector(direction)
            self.status_label.config(text="Status: Auto-paused (decay compensation)", fg="orange")
            return

        x = self.cx
        y = self.cy
        
        if self.increment_time==True:
            detection_duration = self.increment_detection_time(self.decay_constant, self.detection_time, self.direction_at_resume)
            self.log_data(x, y, detection_duration)
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
            td = (-1 / lamda) * log(exp(-lamda * (k * t_move + s)) + exp(-lamda * td_0) - 1)
            detection_times.append(td - t)
            s = s + (td - t)
        return (td-t)

if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()