# ===============================================
# Script: forced_readout.py =====================
# ===============================================

# Last updated: 2023-01-04
# Made by IDEAS

# ===============================================
# Description ===================================
# ===============================================

# This script performs a forced (baseline)
# readout of one front-end.
# 
# When run, the script toggles MaRes, and then
# programs the chosen front-end with the settings
# below.
#
# We encourage modifying this script to adjust
# it to your own needs.

# ===============================================
# Initialization ================================
# ===============================================

import os
import sys

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *


# forcedReadout -------------------------

# Forced readout from specified channels. To read from 
# all channels, set force_all true.
# NOTE: When read_all is False the testbench might read out 
# channels that are not specified. Usually, a reprogram of
# the ASIC and/or a new log file can solve the issue. Also, 
# if forced readout is disabled on both special channels, 
# the cell-pointer will be included in the first anode readout 
# and the x and y coordinates will be overwritten with the value 255. 
# -------------------------------------------------
# input[0]: pulse num, number of readouts to trigger from each channel. 
# input[1]: asic_id, which asic to program [0,1,2,3].
# input[2]: normal_channels, array with normal channels to enable. 
# input[3]: special_channels, array with special channels to enable. 
# input[4]: force_all, enable all channels for forced readout [True, False]
# input[5]: start_col, forced readout start column.
# input[6]: pulse_len, pulse length. 
# input[7]: pulse_int, pulse interval. 
# input[8]: log_file, name and path of file to log to. If not specified, logs to latest added testbench log file. 
# output: None.
# -------------------------------------------------
def forcedReadout(pulse_num, asic_id, normal_channels=None, special_channels=[0,1], read_all=False, start_col=1, pulse_len=400, pulse_int=15999999, log_file=''):
    # Disable readout from all channels

    if read_all:
        ro_all = 1
    else:
        ro_all = 0
        
    # Enable ASIC readout
    readoutEnable(asic_id)

    time.sleep(1)

    tb.setAsicConfigBitFieldByAddr(bitaddr_ro_all, ro_all, asic_id)
    tb.enableDataLogging(False)
    # Set delay
    sh_delay = 80
    tb.setAsicConfigBitFieldByAddr(bitaddr_sh_delay, sh_delay, asic_id)
    # Disable ro8
    tb.setAsicConfigBitFieldByAddr(bitaddr_ro8, 0, asic_id)
    # Disable ro4b
    tb.setAsicConfigBitFieldByAddr(bitaddr_ro4b, 1, asic_id)
    
    # Disable all triggers 
    triggerAllNormal(1, asic_id)

    if not read_all:
        for channel in normal_channels:
            tb.setAsicConfigBitFieldByAddr(bitaddr_forced_readout_ch0 + channel, 1, asic_id)
        # One special channel should always be enabled.
        for channel in special_channels:
            tb.setAsicConfigBitFieldByAddr(bitaddr_forced_readout_cat0 + channel, 1, asic_id)

    time.sleep(.5)

    tb.writeReadAsicConfig(asic_id)

    # Delay to make sure all registers get updated. 
    time.sleep(1)

    # Create new log file.
    if len(log_file) > 1:
        tb.newDataLogFile(log_file)

    # Enable data logging
    tb.enableDataLogging(True)
    # Disable calibration mode. 
    tb.writeSysReg(addr_dac_cal, 0)
    # Set the number of pulses to read.
    tb.writeSysReg(addr_cal_num, pulse_num)
    # Set start column.
    tb.writeSysReg(addr_start_col, start_col)
    # Enable forced readout.
    tb.writeSysReg(addr_forced_en, 1)
    # Disable read max channel.
    tb.writeSysReg(addr_rd_max_ch, 0)
    # Set max channels readout to 130 so that all channels can be read. 
    tb.writeSysReg(addr_max_ch, 130)
    # Disable dummy data
    tb.writeSysReg(addr_dummy_en, 0)

    time.sleep(1)
    # Execute readout
    tb.writeSysReg(addr_cal_exe, 1)
    print('Forced readout is in progress.')
    print('Pulses: ' + str(pulse_num) + '. Pulse length: ' + str(pulse_len) + '. Pulse interval: ' + str(
        pulse_int) + '. ')


forcedReadout(10, asic_id=0, read_all=True, start_col=1, log_file='logs\\pedestals.bin')
