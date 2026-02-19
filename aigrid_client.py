# stage_client.py
# Python 2.7

import socket
import json


class StageClient(object):

    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port

    def _send(self, payload):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        s.send(json.dumps(payload))
        response = json.loads(s.recv(4096).strip())
        s.close()
        return response

    def connect(self, com_port="COM3"):
        return self._send({"action": "connect", "com_port": com_port})

    def move_absolute(self, x, y):
        return self._send({"action": "move_absolute", "x": x, "y": y})

    def home(self):
        return self._send({"action": "home"})

    def stop(self):
        return self._send({"action": "stop"})

    def get_position(self):
        return self._send({"action": "get_position"})

    def disconnect(self):
        return self._send({"action": "disconnect"})

    def set_speed(self, speed):
        """Send speed setting to server"""
        return self._send({"action": "set_speed", "speed": speed})
