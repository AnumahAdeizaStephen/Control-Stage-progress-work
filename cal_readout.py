# ===============================================
# Script: cal_readout.py ========================
# ===============================================

# Last updated: 2023-01-04
# Made by IDEAS

# ===============================================
# Description ===================================
# ===============================================

# This script performs cal pulse readouts
# readout of one front-end.
#
# We encourage modifying this script to adjust
# it to your own needs.
# ===============================================
# Initialization ================================
# ===============================================


import sys
import os

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *


# calPulseReadout ---------------------------------

# Script for cal pulsing a specified channel. 
# -------------------------------------------------
# input[0]: test_ch, channel to trigger.
# input[1]: asic_id, asic_id [0,1,2,3].
# input[2]: cal_dac, cal pulse dac value.
# input[3]: pulse_num, number of pulses to send. Pulse_num = 0 means continuous pulses. 
# input[4]: pulse_len, pulse length.
# input[5]: pulse_int, pulse interval.
# input[6]: log_file, name and path of file to log to. If not specified, logs to latest added testbench log file.
# Output: None.
# -------------------------------------------------
def calPulseReadout(test_ch, asic_id, cal_dac=200, pulse_num=0, pulse_len=400, pulse_int=15999999, log_file=''):
    # Disable ASICs
    tb.writeSysReg(addr_asic_en, 1)
    # Do a master reset
    tb.writeSysReg(addr_mares, 1)

    time.sleep(.5)

    # Disable all channel triggers
    triggerAllNormal(1, asic_id)
    triggerAllSpecial(1, asic_id)

    # Enable one special channel to avoid overwriting the x and y coordinates in the normal channel.
    enableForcedSpecial(0, asic_id)

    # Enable test on 
    testOn(test_ch, asic_id)

    # Disable readout all.
    ro_all = 0
    tb.setAsicConfigBitFieldByAddr(bitaddr_ro_all, ro_all, asic_id)

    # Disable neighbor readouts
    tb.setAsicConfigBitFieldByAddr(bitaddr_ro8, 0, asic_id)
    tb.setAsicConfigBitFieldByAddr(bitaddr_ro4b, 1, asic_id)

    # Set delay    
    sh_delay = 80
    tb.setAsicConfigBitFieldByAddr(bitaddr_sh_delay, sh_delay, asic_id)
    # Set low Gain. A higher gain can be used, however tha cal pulse amplitude need to be adjusted accordingly to
    # avoid saturation.
    tb.setAsicConfigBitFieldByAddr(bitaddr_gain_c3b, 0, asic_id)

    time.sleep(.5)

    tb.writeReadAsicConfig(asic_id)

    time.sleep(1)

    # Create new log file.
    if len(log_file) > 1:
        tb.newDataLogFile(log_file)

    # Enable logging. 
    tb.enableDataLogging(True)

    # Set calibration pulse value
    tb.writeSysReg(addr_dac_cal, cal_dac)

    # Set number of pulses. Pulse_num = 0 means continuous pulses. 
    tb.writeSysReg(addr_cal_num, pulse_num)

    # Disable forced readout
    tb.writeSysReg(addr_forced_en, 0)

    # Disable dummy data
    tb.writeSysReg(addr_dummy_en, 0)

    # Longer delay to make sure everything is configured. 
    time.sleep(2)

    # Execute readout. 
    tb.writeSysReg(addr_cal_exe, 1)

    print('Cal readout started.')

calPulseReadout(4,0)