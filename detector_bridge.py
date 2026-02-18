# detector_bridge.py
# MUST run inside IDEAS Testbench (Python 2)
import sys
import socket
import json
import time
import os
sys.path.append(r"C:\Users\Localadmin_adeizaan\Desktop\Test_bench\IDEASTestbench_V1_6_4_1\scripts\GDS-100")

from tb_product import *
from math import *

HOST = "127.0.0.1"
PORT = 10000

decay_constant = log(2) / (4 * 60)

def increment_detection_time(lamda, td_0, i):
    t = 0
    td = td_0
    t_move = 53
    s = td - t

    for k in range(1, i + 1):
        t = td + t_move
        td = (-1 / lamda) * log(exp(-lamda * (k * t_move + s)) + exp(-lamda * td_0) - 1)
        s = s + (td - t)

    return (td - t)


def log_data(x, y, duration):

    timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")

    if not os.path.exists("logs"):
        os.makedirs("logs")

    filename = "logs/scan_x%.3f_y%.3f_%s.bin" % (x, y, timestamp)

    tb.newDataLogFile(filename)
    tb.enableDataLogging(True)

    time.sleep(duration)

    tb.enableDataLogging(False)

    return filename


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)

print("Detector Bridge running on port 10000")

while True:
    client, addr = server.accept()
    data = client.recv(4096)
    cmd = json.loads(data)

    if cmd["action"] == "log":
        filename = log_data(cmd["x"], cmd["y"], cmd["duration"])
        response = {"status": "success", "file": filename}

    elif cmd["action"] == "increment":
        td = increment_detection_time(decay_constant,
                                      cmd["base_time"],
                                      cmd["index"])
        response = {"status": "success", "duration": td}

    else:
        response = {"status": "error"}

    client.send(json.dumps(response))
    client.close()