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

class XYStepper:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER")
        self.output = None
        self.steps_per_mm = int(6 / 0.5 * 3200)  # Calculate steps per mm for stepper motor
        self.d_between_s = 0.5  # Distance between samples in mm
        self.sx = 0  # Start X position
        self.cx = 0  # Current X position
        self.sy = 0  # Start Y position
        self.cy = 0  # Current Y position
        self.stop_requested = False  # Flag to stop movement

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

    def init_ui(self):
        # Initialize the user interface elements
 	tk.Button(self.root, text="Apply X", command=self.apply_x).grid(row=1, column=0)
        tk.Button(self.root, text="Apply Y", command=self.apply_y).grid(row=1, column=1)
        tk.Button(self.root, text="Zero", command=self.zero).grid(row=3, column=0, columnspan=2)
        tk.Button(self.root, text="Connect", command=self.connect).grid(row=5, column=0)
        tk.Button(self.root, text="Disconnect", command=self.disconnect).grid(row=5, column=1)
        tk.Button(self.root, text="Start 3mm Movement", command=self.start_3mm_movement).grid(row=6, column=0)
        tk.Button(self.root, text="Stop Movement", command=self.stop_movement).grid(row=6, column=1)

        self.x_pos = tk.Label(self.root, text="0")  # Label to display current X position
        self.x_pos.grid(row=7, column=0)
        self.y_pos = tk.Label(self.root, text="0")  # Label to display current Y position
        self.y_pos.grid(row=7, column=1)


    def apply_x(self):
        try:
            x_val = float(self.x_value.get())
            x_val *= self.steps_per_mm
            coordinate = 'x{}'.format(int(x_val))
            self.send_command(coordinate)
            self.x_pos.config(text=str(x_val / self.steps_per_mm))
        except ValueError:
            print("Invalid input for X value. Please enter a valid number.")

    def apply_y(self):
        try:
            y_val = float(self.y_value.get())
            y_val *= self.steps_per_mm
            coordinate = 'y{}'.format(int(y_val))
            self.send_command(coordinate)
            self.y_pos.config(text=str(y_val / self.steps_per_mm))
        except ValueError:
            print("Invalid input for Y value. Please enter a valid number.")
    def start_3mm_movement(self):
        self.stop_requested = False
        print("Welcome to AI-GRID measurement, getting ready...")
        self.root.after(5000, lambda: self.start_detector(0, 0, initial=True))  # 5 seconds delay before starting

    def perform_step(self, run_number, direction):
        if self.stop_requested:
            print("Movement stopped by user.")
            return

        elif self.cx == 2 * self.steps_per_mm and self.cy == 2 * self.steps_per_mm:  #for the last cell, we do not call the start_detector function because that would create a never-ending loop
        #this test is done at the beginning of the code to make sure that the code ends            
            x = self.cx / self.steps_per_mm #we are doing exactly the same thing as it is done in start_detector
            y = self.cy / self.steps_per_mm
            self.tb_enable_data_logging(True)  
            self.log_data(run_number, x, y, 30)  
            print("Completed the entire 3x3 grid movement.")
            self.tb_enable_data_logging(False)  # Turn off the detector
            return

        elif self.cx < 2 * self.steps_per_mm and self.cy == 0: 
            self.root.after(50000, lambda: self.start_detector(run_number, direction + 1))
            self.move_1mm_x()
            return 
        elif self.cx == 2 * self.steps_per_mm and self.cy < self.steps_per_mm:  
            self.root.after(50000, lambda: self.start_detector(run_number, direction + 1))
            self.move_1mm_y()
            return
        elif self.cx > 0 and self.cy == self.steps_per_mm: 
            self.root.after(50000, lambda: self.start_detector(run_number, direction + 1))
            self.move_1mm_x(reverse=True)
            return
        elif self.cx == 0 and self.cy < 2 * self.steps_per_mm:
            self.root.after(50000, lambda: self.start_detector(run_number, direction + 1))
            self.move_1mm_y()
            return
        elif self.cx < 2 * self.steps_per_mm and self.cy == 2 * self.steps_per_mm:
            self.root.after(50000, lambda: self.start_detector(run_number, direction + 1))
            self.move_1mm_x()
            return


    def update_position(self):
        if self.cx < 2 * self.steps_per_mm and self.cy == 0: 
            self.move_1mm_x()
        elif self.cx == 2 * self.steps_per_mm and self.cy < self.steps_per_mm:  
            self.move_1mm_y()
        elif self.cx > 0 and self.cy == self.steps_per_mm: 
            self.move_1mm_x(reverse=True)
        elif self.cx == 0 and self.cy < 2 * self.steps_per_mm:
            self.move_1mm_y()
        elif self.cx < self.steps_per_mm and self.cy == 2 * self.steps_per_mm:
            self.move_1mm_x()
        elif self.cx == self.steps_per_mm and self.cy == 2 * self.steps_per_mm:
            self.move_1mm_x()

    def stop_movement(self):
        self.stop_requested = True

    def move_1mm_x(self, reverse=False):
        # Function to move 1mm in X direction
        self.tb_enable_data_logging(False)  # Turn off the detector
        x_val = self.cx - self.steps_per_mm if reverse else self.cx + self.steps_per_mm
        coordinate = 'Cx{}y{}'.format(int(x_val), int(self.cy))
        self.send_command(coordinate)
        self.cx = x_val
        self.x_pos.config(text=str(self.cx / self.steps_per_mm))

    def move_1mm_y(self):
        # Function to move 1mm in Y direction
        self.tb_enable_data_logging(False)  # Turn off the detector
        y_val = self.cy + self.steps_per_mm
        coordinate = 'Cx{}y{}'.format(int(self.cx), int(y_val))
        self.send_command(coordinate)
        self.cy = y_val
        self.y_pos.config(text=str(self.cy / self.steps_per_mm))

    def zero(self):
        # Zero the X and Y coordinates
        self.tb_enable_data_logging(False)  # Turn off the detector
        self.send_command('Zero')
        self.cx = 0
        self.cy = 0
        self.x_pos.config(text='0')
        self.y_pos.config(text='0')

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
    def log_data(self, run_number, x, y, duration):
        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
        filename = 'logs/Testrun{}_x{}_y{}_{}.bin'.format(run_number, x, y, timestamp)
        tb.newDataLogFile(filename)
        tb.enableDataLogging(True)
        print('Detector On.')
        print('Started data recording at (x={}, y={}).'.format(x, y))
        time.sleep(duration)
        tb.enableDataLogging(False)
        print('Stopped data recording at (x={}, y={})'.format(x, y))
        print('Detector Off.')

    def start_detector(self, run_number, direction, initial=False):
        if initial:
            x, y = 0, 0
        else:
            x = self.cx / self.steps_per_mm
            y = self.cy / self.steps_per_mm
        self.tb_enable_data_logging(True)  # Turn on the detector
        self.log_data(run_number, x, y, 30)  # Log data for 30 seconds
        if initial:
            self.root.after(3000, lambda: self.perform_step(run_number, direction))  # Schedule next step after 3 seconds
        else:
            self.root.after(3000, lambda: self.perform_step(run_number, direction))

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