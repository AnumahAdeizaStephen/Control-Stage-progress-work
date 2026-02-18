# ===============================================
# Script: pedestal_calculation.py ===============
# ===============================================

# Last updated: 2024-03-04
# Made by IDEAS
# ===============================================
# Description ===================================
# ===============================================

import os
import sys
import struct
import time
from datetime import datetime
import numpy as np

sys.path.append(os.getcwd() + '\\logs\\')
sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')

from tb_product import *

import tb_product as tb_product
reload(tb_product)

# ----------pedestal helper functions---------------------------------------------

def load_pedestals_from_bin_file(file_path, forced_start_column = 1, sh_delay = 80):

    packetsize = 352
    pedestal_arr = np.array([[[0]*160 for j in range(15)] for i in range(15)])
    
    with open(file_path, 'rb') as binary_file:

        chunksize = 10*127
        data = bytearray(binary_file.read(packetsize*chunksize))

        start=0
        readout_count = 0
        for i in range(0,chunksize):
            
            d = struct.unpack('>HH HHHB B I BBH L L BB BB 160H', data[start:(start + packetsize)])
            column_pointer = d[14]

            x = d[15]
            y = d[16]
            
            if x == 15:
                x = 12
            if y == 15:
                y = 12
                
            # Cathode readout
            if x == 255:
                readout_count+=1
                x = 13
                y = 13     
            if x == 0:
                x = 14
                y = 14       
                 
            if x == 0 or x == 255 or x == 15 or y == 15:

                print(x, y)
                # Cathode readout                 
                if x==0:
                    readout_count+=1
                start += 352
                continue
            
            
            pedestals = np.array(d[17:])
            
            pedestal_arr[x][y] += pedestals
                      
            start += 352
    
    start_index = 160-(sh_delay-2)-column_pointer #160 - hold delay - column_pointer

    pedestal_arr = pedestal_arr/readout_count
    # TODO: pedestals with different forced readout start to avoid edge artifacts

    binary_file.close()      
    for x in range(len(pedestal_arr)):
        for y in range(len(pedestal_arr[x])):
            # Subtract each value in array from the max value.          
            pedestal_arr[x][y] = max(pedestal_arr[x][y]) - pedestal_arr[x][y]
            # The assumption is that the pedestal variations is within a byte(255). However if the variation is larger for a cell, we need to avoid overflow.
            for i in range(len(pedestal_arr[x][y])):
                if pedestal_arr[x][y][i] > 255:
                    pedestal_arr[x][y][i] = 255
                       
            # Rearrange pedestals so they start on Cell0.    
            ped_a = pedestal_arr[x][y][:start_index]
            ped_b = pedestal_arr[x][y][start_index:]
            pedestal_arr[x][y] = np.concatenate((ped_b, ped_a), axis = None)          
   
    pedestal_list = pedestal_arr.tolist()

    return pedestal_list

#Transform with: 
def ped_transform_op(input_array):
    # Reshape the input array into a 2D array with 40 rows and 4 columns
    two_dimensional_array = [input_array[i:i+4] for i in range(0, len(input_array), 4)]
    result_array = [row[0] + row[1] * 2**8 + row[2] * 2**16 + row[3] * 2**24 for row in two_dimensional_array]

    return result_array
    
#Load into ped ram:
def write_pedestals_into_ped_ram(pedestals, asic_id = 0, anode = True, cathode = True):
    pedram_start = 0x00020000 + asic_id*0x4000
    # Load cathode pedestals for both cathodes
    if cathode:
        ped_byte_array = ped_transform_op(pedestals[13][13])
        xy_chan = 0x00
        print('writing cathode pedestals')
        tb.writeSysReg(addr_pedram_mode_addr, pedram_start + xy_chan*0x40)   # Readback: control + awaddr   
        time.sleep(0.001) 
        for i in range(len(ped_byte_array)):
        #Delay to allow writeSysReg to finish writing. No delay may result in partial overlap.
            time.sleep(0.001)
            tb.writeSysReg(addr_pedram_data, ped_byte_array[i])
        
        ped_byte_array = ped_transform_op(pedestals[14][14])
        xy_chan = 0x01
        print('writing cathode pedestals')
        tb.writeSysReg(addr_pedram_mode_addr, pedram_start + xy_chan*0x40)   # Readback: control + awaddr    
        time.sleep(0.001)    
        for i in range(len(ped_byte_array)):
        #Delay to allow writeSysReg to finish writing. No delay may result in partial overlap.
            time.sleep(0.001)
            tb.writeSysReg(addr_pedram_data, ped_byte_array[i])
            
    if anode:
        # Write anode pedetals 
        xy_chan = 0x00
        print('Writing anode pedestals')    
        for x in range(1,12):
            for y in range(1, 12):
                print('Channel x:' + str(x) + ' y:' + str(y))
                xy_chan = (x<<4)|y
                ped_byte_array = ped_transform_op(pedestals[x][y])      
                tb.writeSysReg(addr_pedram_mode_addr, pedram_start + xy_chan*0x40)
                time.sleep(0.001)
                for i in range(len(ped_byte_array)):
                    tb.writeSysReg(addr_pedram_data, ped_byte_array[i])
                    #Delay to allow writeSysReg to finish writing. No delay may result in partial overlap.
                    time.sleep(0.001)# Not accurate delay. 
                       
def forced_readout_pedestals(asic_id, log_file,pulse_num = 10, sh_delay = 80, start_col = 1, pulse_len=400, pulse_int=15999999):
    
    # Enable ASIC readout
    tb_product.readoutEnable(asic_id)
    
    # Disable pedestal correction
    tb.writeSysReg(addr_pedram_enable, 0)
    
    # Readout all
    tb.setAsicConfigBitFieldByAddr(bitaddr_ro_all, 1, asic_id)
    
    # Disable all triggers 
    tb_product.triggerAllNormal(1, asic_id)
    
    tb.writeReadAsicConfig(asic_id)

    # Delay to make sure all registers get updated. 
    time.sleep(0.5)

    # Create new log file.
    tb.newDataLogFile(log_file)

    # Enable data logging
    tb.enableDataLogging(True)
    
    # Set delay
    tb.setAsicConfigBitFieldByAddr(bitaddr_sh_delay, sh_delay, asic_id)
    
    # Set the number of pulses to read.
    tb.writeSysReg(addr_cal_num, pulse_num)
    # Set start column.
    tb.writeSysReg(addr_start_col, start_col)
    # Enable forced readout.
    tb.writeSysReg(addr_forced_en, 1)
    
    time.sleep(0.1)
    # Execute readout
    tb.writeSysReg(addr_cal_exe, 1)
    print('Forced readout is in progress.')
    print('Pulses: ' + str(pulse_num) + '. Pulse length: ' + str(pulse_len) + '. Pulse interval: ' + str(
        pulse_int) + '. ')
    print('Estimated time '+str(3*pulse_num/10)+'s')
    time.sleep(3*pulse_num/10)
    time.sleep(2)
    print('Forced readout stopped.')
    # Enable data logging
    tb.enableDataLogging(False)

def return_latest_file(directory):
    latest_timestamp = None
    latest_filename = None
    for filename in os.listdir(directory):
        timestamp_str = filename[-23:-4]
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
        if latest_timestamp == None or timestamp > latest_timestamp:
            latest_timestamp = timestamp
            print(latest_timestamp)
            latest_filename = filename
            print(latest_filename)
    return os.path.join(directory,latest_filename)
            
