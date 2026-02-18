# aigrid_server.py
# Python 3.11

import socket
import json
import time
import os
from math import *
from zaber_motion import Library, Units
from zaber_motion.ascii import Connection

# Import detector
import sys
sys.path.append(r"C:\Users\Localadmin_adeizaan\Desktop\Test_bench\IDEASTestbench_V1_6_4_1\scripts\GDS-100")
# from tb_product import *


class AIGRIDServer:

    def __init__(self, host="localhost", port=9999):
        self.host = host
        self.port = port

        self.connection = None
        self.x_axis = None
        self.y_axis = None

        self.decay_constant = log(2) / (4 * 60)

    # ---------------------------------------------------------
    # Stage Control
    # ---------------------------------------------------------

    def connect(self, com_port="COM3"):
        Library.enable_device_db_store()
        self.connection = Connection.open_serial_port(com_port)
        devices = self.connection.detect_devices()

        if len(devices) < 2:
            raise Exception("Need 2 stages")

        self.x_axis = devices[0].get_axis(1)
        self.y_axis = devices[1].get_axis(1)

        self.x_axis.home()
        self.y_axis.home()

        return {"status": "success", "message": "Stages connected & homed"}

    def move_absolute(self, x, y):
        self.x_axis.move_absolute(x, Units.LENGTH_MILLIMETRES, wait_until_idle=False)
        self.y_axis.move_absolute(y, Units.LENGTH_MILLIMETRES, wait_until_idle=False)

        self.x_axis.wait_until_idle()
        self.y_axis.wait_until_idle()

        return {
            "status": "success",
            "x": self.x_axis.get_position(Units.LENGTH_MILLIMETRES),
            "y": self.y_axis.get_position(Units.LENGTH_MILLIMETRES)
        }

    def get_position(self):
        return {
            "status": "success",
            "x": self.x_axis.get_position(Units.LENGTH_MILLIMETRES),
            "y": self.y_axis.get_position(Units.LENGTH_MILLIMETRES)
        }

    def home(self):
        self.x_axis.home()
        self.y_axis.home()
        return {"status": "success"}

    def stop(self):
        self.x_axis.stop()
        self.y_axis.stop()
        return {"status": "success"}

    def disconnect(self):
        if self.connection:
            self.connection.close()
        return {"status": "success"}

    # ---------------------------------------------------------
    # Detector Control
    # ---------------------------------------------------------

    def log_data(self, x, y, duration):
        timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")

        if not os.path.exists("logs"):
            os.makedirs("logs")

        filename = f'logs/phone_x{x:.3f}_y{y:.3f}_{timestamp}.bin'

        print(f"[SIM] Logging at X={x}, Y={y} for {duration}s")
        time.sleep(duration)

        return {"status": "success", "file": filename}

    # ---------------------------------------------------------
    # Decay Compensation
    # ---------------------------------------------------------

    def increment_detection_time(self, lamda, td_0, i):
        t = 0
        td = td_0
        t_move = 53
        s = td - t

        for k in range(1, i + 1):
            t = td + t_move
            td = (-1 / lamda) * log(exp(-lamda * (k * t_move + s)) + exp(-lamda * td_0) - 1)
            s = s + (td - t)

        return (td - t)

    # ---------------------------------------------------------
    # Command Handler
    # ---------------------------------------------------------

    def handle(self, command_str):
        try:
            cmd = json.loads(command_str)
            action = cmd.get("action")

            if action == "connect":
                return self.connect(cmd.get("com_port", "COM3"))

            elif action == "move_absolute":
                return self.move_absolute(cmd["x"], cmd["y"])

            elif action == "get_position":
                return self.get_position()

            elif action == "home":
                return self.home()

            elif action == "stop":
                return self.stop()

            elif action == "log_data":
                return self.log_data(cmd["x"], cmd["y"], cmd["duration"])

            elif action == "increment_time":
                td = self.increment_detection_time(
                    self.decay_constant,
                    cmd["base_time"],
                    cmd["index"]
                )
                return {"status": "success", "duration": td}

            elif action == "disconnect":
                return self.disconnect()

            else:
                return {"status": "error", "message": "Unknown action"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ---------------------------------------------------------
    # TCP Server
    # ---------------------------------------------------------

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(1)

        print(f"AIGRID Server listening on {self.host}:{self.port}")

        while True:
            client, addr = server.accept()
            try:
                while True:
                    data = client.recv(4096)
                    if not data:
                        break

                    response = self.handle(data.decode().strip())
                    client.send((json.dumps(response) + "\n").encode())
            finally:
                client.close()


if __name__ == "__main__":
    AIGRIDServer().start()