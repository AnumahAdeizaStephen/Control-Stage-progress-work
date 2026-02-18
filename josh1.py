import sys

import Tkinter as tk
sys.path.append(r"C:\Users\Localadmin_adeizaan\Desktop\Test_bench\IDEASTestbench_V1_6_4_1\scripts\GDS-100")

# FIX for IDEAS
if not hasattr(sys, 'argv'):
    sys.argv = ['']

from zaber_client_py2 import ZaberClient
stage = ZaberClient()


def connect():
    print(stage.connect("COM3"))


def move():
    print(stage.move_absolute(10, 10))


def home():
    print(stage.home())


def get_position():
    print(stage.get_position())


def stop():
    print(stage.stop())


def disconnect():
    print(stage.disconnect())


root = tk.Tk()
root.title("Zaber IDEAS Control")

tk.Button(root, text="Connect", command=connect).pack()
tk.Button(root, text="Home", command=home).pack()
tk.Button(root, text="Move 10mm,10mm", command=move).pack()
tk.Button(root, text="Get Position", command=get_position).pack()
tk.Button(root, text="Stop", command=stop).pack()
tk.Button(root, text="Disconnect", command=disconnect).pack()

root.mainloop()