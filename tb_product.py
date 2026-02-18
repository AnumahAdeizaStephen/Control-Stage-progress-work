# ===============================================
# Script: tb_product.py =========================
# ===============================================

# Last updated: 2023-01-04
# Made by IDEAS

# ===============================================
# Description ===================================
# ===============================================

# This script contains global testbench settings
# for the GDS-100, that can be used by other
# scripts.

# Names are given to all system registers and
# ASIC module registers so that the user doesn't
# need to work with the numeric addresses.

# ===============================================
# Initialization ================================
# ===============================================

import sys, os
import time

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from system_registers import *
from __main__ import tb


# ===============================================
# Functions =====================================
# ===============================================

# triggerAllNormal ------------------------------------

# Enables or disables triggers for all normal channels.
# Setting 0: all triggers disabled
# Setting 1: all triggers enabled
# -------------------------------------------------
# input[0]: setting, [0,1]
# input[1]: asic_id, [0,1,2,3]
# Output: None.
# -------------------------------------------------
def triggerAllNormal(setting, asic_id):
    for addr in range(bitaddr_trigger_dis_ch0, bitaddr_trigger_dis_ch127 + 1):
        tb.setAsicConfigBitFieldByAddr(addr, setting, asic_id)


# triggerAllSpecial -------------------------
# Enables or disables triggers for all special channels.
# Setting 0: all triggers enabled
# Setting 1: all triggers disabled
# -------------------------------------------------
# input[0]: setting, [0,1]
# input[1]: asic_id, [0,1,2,3]
# Output: None.
# -------------------------------------------------
def triggerAllSpecial(setting, asic_id):
    tb.setAsicConfigBitFieldByAddr(bitaddr_trigger_dis_cat0, setting, asic_id)
    tb.setAsicConfigBitFieldByAddr(bitaddr_trigger_dis_cat1, setting, asic_id)


# triggerEnableNormal -------------------------

# Enables the trigger for the specified normal channel.
# -------------------------------------------------
# input[0]: channel, channel number.
# input[1]: asic_id, [0,1,2,3].
# output: None.
# -------------------------------------------------
def triggerEnableNormal(channel, asic_id):
    tb.setAsicConfigBitFieldByAddr(bitaddr_trigger_dis_ch0 + channel, 0, asic_id)


# triggerEnableSpecial -------------------------

# Enables the trigger for the specified special channel.
# -------------------------------------------------
# input[0]: channel, channel number.
# input[1]: asic_id, [0,1,2,3].
# output: None.
# -------------------------------------------------
def triggerEnableSpecial(channel, asic_id):
    tb.setAsicConfigBitFieldByAddr(bitaddr_trigger_dis_cat0 + channel, 0, asic_id)


# enableForcedSpecial -------------------------------

# Enables forced readout for chosen special channel.
# ----------------------------------------------------
# input[0]: channel, [0,1].
# input[1]: asic_id, [0,1,2,3].
def enableForcedSpecial(channel, asic_id):
    tb.setAsicConfigBitFieldByAddr(bitaddr_forced_readout_cat0 + channel, 1, asic_id)

# forcedAllSpecial -----------------------------------

# Enables or disables forced readout for all special channels.
# Setting 0: forced readout disabled
# Setting 1: forced readout enabled
# -------------------------------------------------
# input[0]: setting, [0,1]
# input[1]: asic_id, [0,1,2,3]
# Output: None.
# -------------------------------------------------
def forcedAllSpecial(setting, asic_id):
    tb.setAsicConfigBitFieldByAddr(bitaddr_forced_readout_cat0, setting, asic_id)
    tb.setAsicConfigBitFieldByAddr(bitaddr_forced_readout_cat1, setting, asic_id)

# testOn ----------------------------------------

# Turns test enable off for all channels except the 
# chosen channel which is turned on.
# Enables the trigger for the chosen channel
# -------------------------------------------------
# input[0]: channel, channel to enable test on.
# input[1]: asic_id, [0,1,2,3].
# output: None.
# -------------------------------------------------
def testOn(channel, asic_id):
    tb.setAsicConfigBitFieldByAddr(bitaddr_test_on, 1, asic_id)

    for addr in range(bitaddr_test_enable_ch0, bitaddr_test_enable_ch127 + 1):
        tb.setAsicConfigBitFieldByAddr(addr, 0, asic_id)

    tb.setAsicConfigBitFieldByAddr(bitaddr_test_enable_ch0 + channel, 1, asic_id)
    tb.setAsicConfigBitFieldByAddr(bitaddr_trigger_dis_ch0 + channel, 0, asic_id)


# readoutEnableList ---------------------------------

# Enables readout for the selected ASIC modules
# -------------------------------------------------
# Input[0]: List with integers (0-3), for instance [1,3] for enabling module 1 and 3
# output: None.
# -------------------------------------------------
def readoutEnableList(asic_id_list):
    binary_asic_ids = ['0'] * 4
    if (0 in asic_id_list):
        binary_asic_ids[3] = '1'
    if (1 in asic_id_list):
        binary_asic_ids[2] = '1'
    if (2 in asic_id_list):
        binary_asic_ids[1] = '1'
    if (3 in asic_id_list):
        binary_asic_ids[0] = '1'

    binary_asic_concat = ''.join(binary_asic_ids)
    decimal_asic_ids = int(binary_asic_concat, 2)

    tb.writeSysReg(addr_asic_en, decimal_asic_ids)


# readoutEnable ---------------------------------

# Enables readout for the selected ASIC module
# 0-3 enables the corresponding module.
# 0 disables readout for all modules.
# -------------------------------------------------
# input[0]: asic_id, [0,1,2,3]
# output: None.
# -------------------------------------------------
def readoutEnable(asic_id):
    if (asic_id == 0):
        decimal_asic_id = 1
    elif (asic_id == 1):
        decimal_asic_id = 2
    elif (asic_id == 2):
        decimal_asic_id = 4
    elif (asic_id == 3):
        decimal_asic_id = 8
    else:
        decimal_asic_id = 0

    tb.writeSysReg(addr_asic_en, decimal_asic_id)


# setHV -----------------------------------------

# Configures the high voltage. It will increment the
# value according to the step value and step_delay. Ramping
# the voltage level is always recommended.
# -------------------------------------------------
# input[0]: Voltage level as DAC value.
# input[1]: Step size for ramping up the HV level.
# input[2]: Delay between each increment.
# Output: None.
# -------------------------------------------------
def setHV(voltage_dac, step=50, step_delay=0.5):
    HV_setting = tb.getSysRegValue(addr_dac_hvctrl)
    v_step = step
    if HV_setting > voltage_dac:
        v_step = -step
    for v in range(HV_setting, voltage_dac + 1, v_step):
        tb.writeSysReg(addr_dac_hvctrl, v)
        print('HV ramping... set to ' + str(v) + ' DAC')
        time.sleep(step_delay)
    tb.writeSysReg(addr_dac_hvctrl, (voltage_dac))
    time.sleep(step_delay)
    time.sleep(2)  # Allow for a some delay in updating the registers.
    print('HV set to ' + str(tb.getSysRegValue(addr_dac_hvctrl)) + ' DAC.')
    # Note: the HV gen monpin might not be updated correctly
    print('HV gen monpin: ' + str(tb.getSysRegValue(addr_mon_hv)))


# createLogFile -----------------------------------

# Creates new log file and enables logging. 
# -------------------------------------------------
# input[0]: datalog_filename, name for new logfile(.bin) with path.
# Output: None.
# -------------------------------------------------
def createLogFile(datalog_filename):
    tb.enableDataLogging(False)
    tb.newDataLogFile(datalog_filename)
    tb.enableDataLogging(True)
    print('Now logging to: ' + datalog_filename)
