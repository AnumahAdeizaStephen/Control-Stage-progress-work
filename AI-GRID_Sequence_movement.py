import Tkinter as tk  # Import Tkinter for GUI
import serial  # Import pySerial for serial communication
import sys  # Import sys module to access system-specific parameters and functions
import os  # Import os module for operating system related functions
import atexit  # Import atexit to handle cleanup on program exit

# Ensure sys.argv is available
if not hasattr(sys, 'argv'):
    sys.argv = ['']

class XYStepper:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-GRID CONTROLLER")
        self.output = None
        self.steps_per_mm = int(6 / 0.5 * 3200)  # Calculate steps per mm for stepper motor
        self.geometry = 'Measure5'  # Geometry type for measurements
        self.number_of_samples = 1  # Number of samples to measure
        self.number_of_points = 4  # Number of points per sample
        self.sample_names = ['2810753-5']  # Sample names
        self.d_between_s = 0.5  # Distance between samples in mm
        self.sx = 0  # Start X position
        self.cx = 0  # Current X position
        self.sy = 0  # Start Y position
        self.cy = 0  # Current Y position
        self.stop_requested = False  # Flag to stop movement

        self.a = None  # Initialize serial connection to None

        try:
            self.connect_serial()  # Connect to the serial port
            self.init_coordinates()  # Initialize coordinates based on geometry
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

    def init_coordinates(self):
        # Initialize coordinates based on the selected geometry
        if self.geometry == 'Measure5':
            self.x_coordinates = [0] * self.steps_per_mm  # X coordinates array
            self.y_coordinates = [0] * self.steps_per_mm  # Y coordinates array

            self.samples_x = []  # Sample X positions
            self.samples_y = []  # Sample Y positions

            for j in range(self.number_of_samples):
                for i in range(len(self.x_coordinates)):
                    self.samples_x.append(self.x_coordinates[i])
                    self.samples_y.append(self.y_coordinates[i] + (j * self.d_between_s * self.steps_per_mm))

        elif self.geometry == 'Measure16':
            self.x_coordinates = [(0 + (i * 3.0 / (self.number_of_points - 1))) * self.steps_per_mm for i in range(self.number_of_points)]
            self.y_coordinates = [(0 + (i * 3.0 / (self.number_of_points - 1))) * self.steps_per_mm for i in range(self.number_of_points)]

            self.samples_x = []  # Sample X positions
            self.samples_y = []  # Sample Y positions

            for j in range(self.number_of_samples):
                for i in range(self.number_of_points):
                    self.samples_x.append(self.x_coordinates[i])
                    self.samples_y.append(self.y_coordinates[i] + (j * self.d_between_s * self.steps_per_mm))

    def init_ui(self):
        # Initialize the user interface elements
        tk.Button(self.root, text="Zero", command=self.zero).grid(row=3, column=0, columnspan=2)
        tk.Button(self.root, text="Connect", command=self.connect).grid(row=5, column=0)
        tk.Button(self.root, text="Disconnect", command=self.disconnect).grid(row=5, column=1)
        tk.Button(self.root, text="Start 3mm Movement", command=self.start_3mm_movement).grid(row=6, column=0)
        tk.Button(self.root, text="Stop Movement", command=self.stop_movement).grid(row=6, column=1)

        self.x_pos = tk.Label(self.root, text="0")  # Label to display current X position
        self.x_pos.grid(row=7, column=0)
        self.y_pos = tk.Label(self.root, text="0")  # Label to display current Y position
        self.y_pos.grid(row=7, column=1)

    def start_3mm_movement(self):
        self.stop_requested = False
        self.perform_step(0, 0)

    def perform_step(self, step, direction):
        if self.stop_requested:
            print("Movement stopped by user.")
            return
        if direction == 0:
            if step < 3:
                print("Moving 1mm step {}/3 on X-axis".format(step + 1))
                self.move_1mm_x()
                self.root.after(30000, lambda: self.perform_step(step + 1, direction))  # Schedule next step after 30 seconds
            else:
                print("Completed 3 steps on X-axis. Moving 1mm on Y-axis.")
                self.move_1mm_y()
                self.root.after(30000, lambda: self.perform_step(0, 1))  # Schedule next step after 30 seconds
        elif direction == 1:
            if step < 3:
                print("Returning 1mm step {}/3 on X-axis".format(step + 1))
                self.move_1mm_x(reverse=True)
                self.root.after(30000, lambda: self.perform_step(step + 1, direction))  # Schedule next step after 30 seconds
            else:
                print("Completed 3 steps back on X-axis. Moving 1mm on Y-axis.")
                self.move_1mm_y()
                self.root.after(30000, lambda: self.perform_step(0, 2))  # Schedule next step after 30 seconds
        elif direction == 2:
            if step < 3:
                print("Moving 1mm step {}/3 on X-axis".format(step + 1))
                self.move_1mm_x()
                self.root.after(30000, lambda: self.perform_step(step + 1, direction))  # Schedule next step after 30 seconds
            else:
                print("Completed the entire 3x3 grid movement.")

    def stop_movement(self):
        self.stop_requested = True

    def move_1mm_x(self, reverse=False):
        # Function to move 1mm in X direction
        x_val = self.cx - (self.steps_per_mm // 2) if reverse else self.cx + (self.steps_per_mm // 2)
        coordinate = 'Cx{}y{}'.format(int(x_val), int(self.cy))
        self.send_command(coordinate)
        self.cx = x_val
        self.x_pos.config(text=str(self.cx / self.steps_per_mm))

    def move_1mm_y(self):
        # Function to move 1mm in Y direction
        y_val = self.cy + (self.steps_per_mm // 2)
        coordinate = 'Cx{}y{}'.format(int(self.cx), int(y_val))
        self.send_command(coordinate)
        self.cy = y_val
        self.y_pos.config(text=str(self.cy / self.steps_per_mm))

    def zero(self):
        # Zero the X and Y coordinates
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

if __name__ == "__main__":
    root = tk.Tk()
    app = XYStepper(root)
    root.mainloop()