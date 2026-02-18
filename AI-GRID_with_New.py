import Tkinter as tk  # Import Tkinter for GUI
import serial  # Import pySerial for serial communication
import sys  # Import sys module to access system-specific parameters and functions
import os  # Import os module for operating system related functions
import atexit  # Import atexit to handle cleanup on program exit
import time  # Import time module for timestamp and sleep functions

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *  # Import tb_product module

# Ensure sys.argv is available
if not hasattr(sys, 'argv'):
    sys.argv = ['']

'''
You have to click on all of the 3 Save buttons to save the values in the tk.Entry before running "Go to this position 
(x,y)", "Launch a single scan by the detector at (x,y)" and "Start 26mm Movement" buttons.
'''

class XYStepper:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER")
        self.output = None
        self.steps_per_mm = int(6 / 0.5 * 3200)  # Calculate steps per mm for stepper motor
        self.d_between_s = 0.5  # Distance between samples in mm
        self.cx = 0  # Current X position 
        self.cy = 0  # Current Y position
        self.stop_requested = False  # Flag to stop movement
        self.detection_time = 30 # Default value of the detection time
        self.grid_size = 2 

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

###########################################################################################################################
# NEW METHODS FOR MANUAL INTERFACE

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

###########################################################################################################################
# NEW : buttons to choose the steps, the starting point for x and y and the time of detection

        # Manual interface that allows the user to choose a position 
        tk.Label(self.root, text="Enter a value for x :").grid(row=10, column=0)
        self.entry_cx = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.entry_cx.insert(0, "0")  # Default value
        self.entry_cx.grid(row=10, column=1)  # Displays it
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_cx)).grid(row=10, column=2) #Saves it

        tk.Label(self.root, text="          ").grid(row = 10, column = 3)

        tk.Label(self.root, text="Enter a value for y :").grid(row=10, column=4)
        self.entry_cy = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.entry_cy.insert(0, "0")  # Default value
        self.entry_cy.grid(row=10, column=5)  # Displays it
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_cy)).grid(row=10, column=6) #Saves it

        # Button to move to the starting position
        tk.Button(self.root, text="Go to this position (x,y)", command=self.move_to_starting_point).grid(row=11, column=1)

        # Choose the x and y step
        #TO DO (issue if we are out of range ?) 

        # Choose the detection time 
        tk.Label(self.root, text="Enter detection time (in seconds):").grid(row=9, column=0)
        self.entry_duration = tk.Entry(self.root, validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
        self.entry_duration.insert(0, "30")  # Default value
        self.entry_duration.grid(row=9, column=1)  # Displays it
        tk.Button(self.root, text="Save", command=lambda: self.save_value(self.entry_duration)).grid(row=9, column=2) #Saves it

        # Button to use the detector once, for the detection time indicated entry_duration
        tk.Button(self.root, text="Launch a single scan by the detector at (x,y)", command=self.run_detection_only).grid(row=11, column=4) 

###########################################################################################################################     
###########################################################################################################################

        self.x_pos = tk.Label(self.root, text="0")  # Label to display current X position
        self.x_pos.grid(row=13, column=1)
        self.y_pos = tk.Label(self.root, text="0")  # Label to display current Y position
        self.y_pos.grid(row=13, column=4)


###########################################################################################################################
# NEW METHODS 
    # To save the values (detection time, x value...) when they are written in the tk.Entry
    def save_value(self, entry_widget):
        value = entry_widget.get()
        if value.replace(".", "", 1).isdigit(): #to check if the value is a positive floating point number
            value_float = float(value)
            if entry_widget == self.entry_cx: #we need to precise that it should be a number that do not reach the maximum value of the grid
                self.cx = int(value_float * self.steps_per_mm)
            elif entry_widget == self.entry_cy: #we need to precise that it should be a number that do not reach the maximum value of the grid
                self.cy = int(value_float * self.steps_per_mm) #maybe we should add a round() inside the int() to save some decimal numbers
            elif entry_widget == self.entry_duration:
                self.detection_time = value_float 
        else:
            print("Invalid number entered.")

    def move_to_starting_point(self):
        self.tb_enable_data_logging(False)  # Turn off the detector
        coordinate = 'Cx{}y{}'.format(int(self.cx), int(self.cy))
        print("Moving to starting point: {coordinate}")
        self.send_command(coordinate)
        self.x_pos.config(text=str(self.cx / self.steps_per_mm))
        self.y_pos.config(text=str(self.cy / self.steps_per_mm))

    def run_detection_only(self):
        duration = self.detection_time
        x = self.cx / self.steps_per_mm
        y = self.cy / self.steps_per_mm
        self.log_data(x, y, duration)
        
        
# run_number was used to give a name to the log files and make them unique. 
# However, is this necessary since the log file names are already unique by using timestamps?
# I have removed the run_number variable everywhere and instead used timestamps to name the log files.

###########################################################################################################################
###########################################################################################################################

    def start_movement(self):
        self.stop_requested = False
        print("Welcome to AI-GRID measurement, getting ready...")
        self.root.after(5000, lambda: self.start_detector(0))  # 5 seconds delay before starting

    def perform_step(self, direction):
        max_steps = self.grid_size * self.steps_per_mm #the maximum max_steps that we could reach with the same measuring system would be 35mm

        x_corr = self.cx - float(self.entry_cx.get()) * self.steps_per_mm
        y_corr = self.cy - float(self.entry_cy.get()) * self.steps_per_mm
       
        if self.stop_requested:
            print("Movement stopped by user.")
            return
        #this test is done at the beginning of the code to make sure that the code ends
        elif x_corr == max_steps and y_corr == max_steps and direction == (self.grid_size + 1) * (self.grid_size + 1) - 1:  #for the last cell, we do not call the start_detector function because that would create a never-ending loop            
                                                                                        # here there was a condition missing if you do an even x even grid (the last line would not be detected)
                                                                                        # issue also if you want to do a 1x1 grid  
            x = self.cx / self.steps_per_mm 
            y = self.cy / self.steps_per_mm
            self.log_data(x, y, self.detection_time)  
            print("Completed the entire grid movement.")
            return
        #if we are on an even line
        elif y_corr % (2 * self.steps_per_mm) == 0 and x_corr < max_steps :
            self.root.after(50000, lambda: self.start_detector(direction + 1))
            self.move_1mm_x()
            return       
        #if we are on an odd line
        elif y_corr % (2 * self.steps_per_mm) != 0 and x_corr > 0 :
            self.root.after(50000, lambda: self.start_detector(direction + 1))
            self.move_1mm_x(reverse=True)
            return       
        #when we are at the end of a line (x=0 or x=25) and we want to go down
        elif y_corr < max_steps and (x_corr == 0 or x_corr == max_steps) :
            self.root.after(50000, lambda: self.start_detector(direction + 1))
            self.move_1mm_y()
            return        
 
    def stop_movement(self):
        self.stop_requested = True

    def move_1mm_x(self, reverse=False):
        # Function to move 1mm in X direction
        x_val = self.cx - self.steps_per_mm if reverse else self.cx + self.steps_per_mm
        coordinate = 'Cx{}y{}'.format(float(x_val), float(self.cy))
        self.send_command(coordinate)
        self.cx = x_val
        self.x_pos.config(text=str(self.cx / self.steps_per_mm))

    def move_1mm_y(self):
        # Function to move 1mm in Y direction
        y_val = self.cy + self.steps_per_mm
        coordinate = 'Cx{}y{}'.format(float(self.cx), float(y_val))
        self.send_command(coordinate)
        self.cy = y_val
        self.y_pos.config(text=str(self.cy / self.steps_per_mm))

    def connect(self):
        # Connect to the serial port
        try:
            self.a.open()
            self.read_until_ready()
        except serial.SerialException as e:
            print("Error connecting to COM4: {}".format(e))
            self.cleanup_serial()

    def disconnect(self):
        # Disconnect from the serial port
        try:
            self.send_command('Stop')
            self.a.close()
        except serial.SerialException as e:
            print("Error disconnecting from COM4: {}".format(e))
            self.cleanup_serial()

    def send_command(self, command):
        # Send a command to the serial device
        try:
            print("Sending command: {}".format(command))  # Debug statement
            self.a.write('{}\n'.format(command).encode())
        except serial.SerialException as e:
            print("Error sending command: {}".format(e))
            self.cleanup_serial()

    def read_until_ready(self):
        # Read from the serial device until 'Ready' is received
        try:
            while True:
                received = self.a.readline().strip()
                print("Received: {}".format(received))  # Debug statement
                if received == 'Ready':
                    break
        except serial.SerialException as e:
            print("Error reading from serial port: {}".format(e))
            self.cleanup_serial()

    # New function to handle detector logging
    def log_data(self, x, y, duration):
        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        filename = 'logs/scan_x{}_y{}_{}.bin'.format(x, y, timestamp)
        tb.newDataLogFile(filename)
        tb.enableDataLogging(True)
        print('Detector On.')
        print('Started data recording at (x={}, y={}).'.format(x, y))
        time.sleep(duration)
        tb.enableDataLogging(False)
        print('Stopped data recording at (x={}, y={})'.format(x, y))
        print('Detector Off.') 

    def start_detector(self, direction): #no need to specify whether it is initials or not because we enter manually a starting point
        x = self.cx / self.steps_per_mm
        y = self.cy / self.steps_per_mm
        #self.tb_enable_data_logging(True) #useless, log_data already does that
        self.log_data(x, y, self.detection_time)
        self.root.after(3000, lambda: self.perform_step(direction))

    # Function to control the detector
    def tb_enable_data_logging(self, enable):
        tb.enableDataLogging(enable)
        if enable:
            print("Detector On.") 
        else:
            print("Detector Off.")

if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()