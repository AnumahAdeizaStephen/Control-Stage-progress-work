# Reads data from a binary IDEAS Testbench Pipeline Readout Data log file
# IDEAS (Integrated Detector Electronics AS) (C) 2022

import struct
import datetime
import time
import shutil

# ---------- SETTINGS -------------
input_filename = "../../logs/2022-11-15__12_28_46__GDS-100__raw_data_log.bin"
output_filename = "../../logs/output_log11.csv"

# -----
STOP_READ = 0

# ------ FUNCTIONS ------
def read_byte(file_rd):
    global STOP_READ
    byte_rd = 0
    try:
        byte_rd = (struct.unpack("B", file_rd.read(1)))[0]
    except:
        STOP_READ = 1
    return byte_rd


def read_word(file_rd):
    global STOP_READ
    word_rd = 0
    try:
        word_rd = (struct.unpack(">H", file_rd.read(2)))[0]
    except:
        STOP_READ = 1
    return word_rd


def read_dword(file_rd):
    global STOP_READ
    dword_rd = 0
    try:
        dword_rd = (struct.unpack(">I", file_rd.read(4)))[0]
    except:
        STOP_READ = 1
    return dword_rd


class CommonLogHeader:
    def __init__(self):
        self.length = 0
        self.log_type = 0
        self.reserved = 0
        self.system_number = 0
        self.timestamp = 0

    def read(self, f):
        self.length = read_word(f)
        self.log_type = read_word(f)
        self.reserved = read_dword(f)
        self.reserved = read_word(f)
        self.reserved = read_byte(f)
        self.system_number = read_byte(f)
        self.timestamp = read_dword(f)

    def write(self, f):
        f.write(str(self.length) + ";")
        f.write(str(self.log_type) + ";")
        f.write(str(self.system_number) + ";")
        f.write(str(self.timestamp) + ";")

    def write_column_header(self, f):
        f.write("length;")
        f.write("log_type;")
        f.write("system_number;")
        f.write("timestamp;")

    def print(self):
        print(self.length)
        print(self.log_type)
        print(self.reserved)
        print(self.system_number)
        print(self.timestamp)


class PipelineMetadata:
    def __init__(self):
        self.source_id = 0
        self.trigger_type = 0
        self.user_status = 0
        self.event_id = 0
        self.pps_timestamp = 0
        self.channel_flag = 0
        self.cell_pointer = 0
        self.x_address = 0
        self.y_address = 0

    def read(self, f):
        self.source_id = read_byte(f)
        self.trigger_type = read_byte(f)
        self.user_status = read_word(f)
        self.event_id = read_dword(f)
        self.pps_timestamp = read_dword(f)
        self.channel_flag = read_byte(f)
        self.cell_pointer = read_byte(f)
        self.x_address = read_byte(f)
        self.y_address = read_byte(f)

    def write(self, f):
        f.write(str(self.source_id) + ";")
        f.write(str(self.trigger_type) + ";")
        f.write(str(self.user_status) + ";")
        f.write(str(self.event_id) + ";")
        f.write(str(self.pps_timestamp) + ";")
        f.write(str(self.channel_flag) + ";")
        f.write(str(self.cell_pointer) + ";")
        f.write(str(self.x_address) + ";")
        f.write(str(self.y_address) + ";")

    def write_column_header(self, f):
        f.write("source_id;")
        f.write("trigger_type;")
        f.write("user_status;")
        f.write("event_id;")
        f.write("pps_timestamp;")
        f.write("channel_flag;")
        f.write("cell_pointer;")
        f.write("x_address;")
        f.write("y_address;")

    def print(self):
        print(self.source_id)
        print(self.trigger_type)
        print(self.user_status)
        print(self.event_id)
        print(self.pps_timestamp)
        print(self.channel_flag)
        print(self.cell_pointer)
        print(self.x_address)
        print(self.y_address)


class PipelineReadout:
    def __init__(self):
        self.data = [0] * 160

    def read(self, f):
        for i in range(0, 160):
            self.data[i] = read_word(f)

    def write(self, f):
        for i in range(0, 160):
            f.write(str(self.data[i]) + ";")

    def write_column_header(self, f):
        for i in range(0, 160):
            f.write("cell_" + str(i) + ";")

    def print(self):
        for i in range(0, 160):
            print(self.data[i])


def readLogFile(logFileName):
    global STOP_READ
    print("**** File Read : " + logFileName + " ******")
    print(" ")
    log_entry = 0
    STOP_READ = 0
    save_file = open(output_filename, "w")
    header = CommonLogHeader()
    header.write_column_header(save_file)
    metadata = PipelineMetadata()
    metadata.write_column_header(save_file)
    readout = PipelineReadout()
    readout.write_column_header(save_file)
    save_file.write("\n")

    with open(logFileName, "rb") as log_file:
        while STOP_READ == 0:
            header.read(log_file)
            header.write(save_file)
            metadata.read(log_file)
            metadata.write(save_file)
            readout.read(log_file)
            readout.write(save_file)
            save_file.write("\n")
            log_entry += 1

    save_file.close()
    print("Logfile Close() ")
    print("Total Log entries: = " + str(log_entry))


# ------ SCRIPT ------
readLogFile(input_filename)
