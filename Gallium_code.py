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
        self.cx = 0  # Current X position 
        self.cy = 0  # Current Y position
        self.stop_requested = False  # Flag to stop movement
        self.paused = False  # Flag to indicate if paused
        self.pending_action = None  # Store what to resume after pause
        self.detection_time = 30 # Default value of the detection time
        self.increment_time = False  # Flag to enable/disable increment for detection time
        self.grid_size = 2 # For the scan of a 26x26 grid 
        self.decay_constant = log(2) / (4 * 60) # For the Gallium 68, in seconds-1
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
    def validate_number(self,entry): 
        return(entry == "" or entry.replace(".", "", 1).isdigit())


###########################################################################################################################
###########################################################################################################################

    def init_ui(self):
        # Initialize the user interface elements
        tk.Button(self.root, text="Connect", command=self.connect).grid(row=5, column=1)
        tk.Button(self.root, text="Disconnect", command=self.disconnect).grid(row=5, column=4)
        tk.Button(self.root, text="Start Snake Movement", command=self.start_movement).grid(row=12, column=1)
        tk.Button(self.root, text="Stop Movement", command=self.stop_movement).grid(row=12, column=4)
        #tk.Button(self.root, text="Pause", command=self.pause).grid(row=12, column=2)  # Add Pause button, not necessary as the program pauses automatically when the activity becomes too low
        tk.Button(self.root, text="Play", command=self.play).grid(row=9, column=6)    # Add Play button

        # Manual interface that allows the user to choose a position (x and y)
        tk.Label(self.root, text="Enter a value for x :").grid(row=10, column=0)
        self.entry_cx = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P")) # To be sure that the entry is a number
        self.entry_cx.insert(0, "0")  # Default value
        self.entry_cx.grid(row=10, column=1)  # Displays it
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_cx)).grid(row=10, column=2) # Saves it

        tk.Label(self.root, text="Enter a value for y :").grid(row=10, column=4)
        self.entry_cy = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P")) # To be sure that the entry is a number
        self.entry_cy.insert(0, "0")  # Default value
        self.entry_cy.grid(row=10, column=5)  # Displays it
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_cy)).grid(row=10, column=6) # Saves it

        # Button to move to the position entered via the entries above
        tk.Button(self.root, text="Go to this position (x,y)", command=self.move_to_position).grid(row=11, column=1)

        # Choose the detection time 
        tk.Label(self.root, text="Enter detection time (in seconds):").grid(row=9, column=0)
        self.entry_duration = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P")) # To be sure that the entry is a number
        self.entry_duration.insert(0, "30")  # Default value
        self.entry_duration.grid(row=9, column=1)  # Displays it
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_duration)).grid(row=9, column=2) # Saves it

        # Choose to enable, or not, the increment for the detection time entered
        tk.Label(self.root, text="Increment for the detection time (Yes=1, No=0)").grid(row=9, column=3)
        self.increment = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P")) # To be sure that the entry is a number
        self.increment.grid(row=9, column=4)  # Displays it
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.increment)).grid(row=9, column=5) # Saves it

        # Button to use the detector once, for the detection time indicated (entry_duration)
        tk.Button(self.root, text="Launch a single scan by the detector at (x,y)", command=self.run_detection_only).grid(row=11, column=4) 
   
        # Labels to display the current X and Y positions
        self.x_pos = tk.Label(self.root, text="0")  # Label to display current X position
        self.x_pos.grid(row=13, column=1)
        self.y_pos = tk.Label(self.root, text="0")  # Label to display current Y position
        self.y_pos.grid(row=13, column=4)


###########################################################################################################################
###########################################################################################################################

    # To save the values (detection time, x value...) when they are written in the tk.Entry
    def save_value(self, entry_widget):
        value = entry_widget.get()
        if value.replace(".", "", 1).isdigit(): # To check if the value is a positive floating point number
            value_float = float(value)
            if entry_widget == self.entry_cx: # We need to precise that it should be a number that do not reach the maximum value of the grid
                self.cx = float(value_float * self.steps_per_mm)
            elif entry_widget == self.entry_cy: # We need to precise that it should be a number that do not reach the maximum value of the grid
                self.cy = float(value_float * self.steps_per_mm) 
            elif entry_widget == self.entry_duration:
                self.detection_time = value_float
            elif entry_widget == self.increment: # To enable or disable the increment for the detection time
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

# To move to the position entered in the x and y entries
    def move_to_position(self):
        self.tb_enable_data_logging(False)  # Turn off the detector
        coordinate = 'Cx{}y{}'.format(float(self.cx), float(self.cy))
        print("Moving to starting point: {coordinate}")
        self.send_command(coordinate)
        self.x_pos.config(text=str(self.cx / self.steps_per_mm))
        self.y_pos.config(text=str(self.cy / self.steps_per_mm))

# To run the detector only once, for the detection time indicated in the entry_duration
    def run_detection_only(self):
        duration = self.detection_time
        x = self.cx / self.steps_per_mm
        y = self.cy / self.steps_per_mm
        self.log_data(x, y, duration)

# To start the snake movement
    def start_movement(self):
        self.stop_requested = False
        self.paused = False
        self.pending_action = None
        self.time_since_beginning = time.time()
        print("Welcome to AI-GRID measurement, getting ready...")
        self.root.after(5000, lambda: self.start_detector(0))  # 5 seconds delay before starting

# To perform the step in the snake movement
    def perform_step(self, direction):
        if self.stop_requested:
            print("Movement stopped by user.")
            return

        if self.paused:
            print("Movement paused at step {}, coordinate ({}, {})".format(direction, self.cx, self.cy))
            self.pending_action = lambda: self.perform_step(direction)
            return
        
        max_steps = self.grid_size * self.steps_per_mm # The maximum max_steps that we could reach with the same measuring system would be 35mm

        x_corr = self.cx - float(self.entry_cx.get()) * self.steps_per_mm
        y_corr = self.cy - float(self.entry_cy.get()) * self.steps_per_mm
       
        if direction == (self.grid_size + 1) * (self.grid_size + 1) - 1:  # The last cell is already scanned thanks to start_detector and the after() methods in the loops below          
            print("Completed the entire grid movement.")
            return
        #if we are on an even line
        elif y_corr % (2 * self.steps_per_mm) == 0 and x_corr < max_steps :
            self.root.after(30000, lambda: self.start_detector(direction + 1))
            self.move_1mm_x()
            return       
        #if we are on an odd line
        elif y_corr % (2 * self.steps_per_mm) != 0 and x_corr > 0 :
            self.root.after(30000, lambda: self.start_detector(direction + 1))
            self.move_1mm_x(reverse=True)
            return       
        #when we are at the end of a line (x=0 or x=25) and we want to go down
        elif y_corr < max_steps and (x_corr == 0 or x_corr == max_steps) :
            self.root.after(30000, lambda: self.start_detector(direction + 1))
            self.move_1mm_y()
            return        
 
# To stop the movement
    def stop_movement(self):
        self.stop_requested = True
        self.paused = False
        self.pending_action = None

# To move 1mm in X direction, either forward or backward
    def move_1mm_x(self, reverse=False):
        x_val = self.cx - self.steps_per_mm if reverse else self.cx + self.steps_per_mm
        coordinate = 'Cx{}y{}'.format(float(x_val), float(self.cy))
        self.send_command(coordinate)
        self.cx = x_val
        self.x_pos.config(text=str(self.cx / self.steps_per_mm))

# To move 1mm in Y direction
    def move_1mm_y(self):
        y_val = self.cy + self.steps_per_mm
        coordinate = 'Cx{}y{}'.format(float(self.cx), float(y_val))
        self.send_command(coordinate)
        self.cy = y_val
        self.y_pos.config(text=str(self.cy / self.steps_per_mm))

# To connect to the serial port
    def connect(self):
        try:
            self.a.open()
            self.read_until_ready()
        except serial.SerialException as e:
            print("Error connecting to COM4: {}".format(e))
            self.cleanup_serial()

# To disconnect from the serial port
    def disconnect(self):
        try:
            self.send_command('Stop')
            self.a.close()
        except serial.SerialException as e:
            print("Error disconnecting from COM4: {}".format(e))
            self.cleanup_serial()
    
# To pause the movement
    def pause(self):
        self.paused = True
        print("Pause requested.")

# To resume the movement after a pause
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

# To send a command to the serial device
    def send_command(self, command):
        try:
            print("Sending command: {}".format(command))  # Debug statement
            self.a.write('{}\n'.format(command).encode())
        except serial.SerialException as e:
            print("Error sending command: {}".format(e))
            self.cleanup_serial()

# To read from the serial device until 'Ready' is received
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

# To handle detector logging
    def log_data(self, x, y, duration):
        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        filename = 'logs/scan_x{}_y{}_{}.bin'.format(x-float(self.entry_cx.get()), y-float(self.entry_cy.get()), timestamp)
        tb.newDataLogFile(filename)
        tb.enableDataLogging(True)
        print('Detector On.')
        print('Started data recording at (x={}, y={}).'.format(x, y))
        time.sleep(duration) 
        tb.enableDataLogging(False)
        print('Stopped data recording at (x={}, y={})'.format(x, y))
        print('Detector Off.') 

# To start the detector 
    def start_detector(self, direction):
        # Automatic pause if increment_detection_time exceeds threshold
        if time.time() - self.time_since_beginning  > -1/self.decay_constant * log(0.5) and self.increment_time==True:
            print("Auto-pause at direction {} (x={}, y={})".format(direction, self.cx, self.cy))
            self.paused = True
            self.pending_action = lambda: self.start_detector(direction)
            return

        x = self.cx / self.steps_per_mm
        y = self.cy / self.steps_per_mm
        
        if self.increment_time==True:
            self.log_data(x, y, self.increment_detection_time(self.decay_constant, self.detection_time, self.direction_at_resume))
        else:
            self.log_data(x, y, self.detection_time)
        self.direction_at_resume = self.direction_at_resume + 1
        self.root.after(3000, lambda: self.perform_step(direction))

# To control the detector
    def tb_enable_data_logging(self, enable):
        tb.enableDataLogging(enable)
        if enable:
            print("Detector On.") 
        else:
            print("Detector Off.")

# Increment for the detection time in order to compensate the source decay
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
        return (td-t)

if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()