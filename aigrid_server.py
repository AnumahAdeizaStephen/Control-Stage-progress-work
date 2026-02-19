# stage_server.py
# Python 3.11

import socket
import json
from zaber_motion import Library, Units
from zaber_motion.ascii import Connection


class StageServer:

    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port
        self.connection = None
        self.x_axis = None
        self.y_axis = None

    # ---------------------------------------------------------
    # Stage Control
    # ---------------------------------------------------------

    def connect(self, com_port="COM3"):
        Library.enable_device_db_store()
        self.connection = Connection.open_serial_port(com_port)
        devices = self.connection.detect_devices()

        if len(devices) < 2:
            raise Exception("Need 2 detected devices")

        self.x_axis = devices[0].get_axis(1)
        self.y_axis = devices[1].get_axis(1)

        self.x_axis.home()
        self.y_axis.home()

        return {"status": "success", "message": "Stages connected & homed"}

    def move_absolute(self, x, y):
        self.x_axis.move_absolute(
            x, Units.LENGTH_MILLIMETRES, wait_until_idle=False
        )
        self.y_axis.move_absolute(
            y, Units.LENGTH_MILLIMETRES, wait_until_idle=False
        )

        self.x_axis.wait_until_idle()
        self.y_axis.wait_until_idle()

        return self.get_position()

    def get_position(self):
        return {
            "status": "success",
            "x": self.x_axis.get_position(Units.LENGTH_MILLIMETRES),
            "y": self.y_axis.get_position(Units.LENGTH_MILLIMETRES),
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

        print("Stage Server listening on %s:%d" % (self.host, self.port))

        while True:
            client, addr = server.accept()
            try:
                data = client.recv(4096)
                if not data:
                    continue

                response = self.handle(data.decode().strip())
                client.send((json.dumps(response) + "\n").encode())

            finally:
                client.close()


if __name__ == "__main__":
    StageServer().start()
