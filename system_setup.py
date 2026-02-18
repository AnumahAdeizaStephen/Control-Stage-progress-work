# ===============================================
# Script: system_setup.py =====================
# ===============================================

# Last updated: 2023-08-23
# Made by IDEAS

# ===============================================
# Description ===================================
# ===============================================

# This is an example on how to configure the system 
# to be ready for triggered readout. 

# We encourage modifying this script to adjust
# it to your own needs.

# ===============================================
# Initialization ================================
# ===============================================

import sys
import os

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *

# ===============================================
# Settings ======================================
# ===============================================

readout_enable_asics = [0]  # ASICs to enable. Note: All other ASICs will be disabled.

gain_level = 3  # Level 1: up to 9MeV, Level 2: up to 7MeV, Level 3: up to 3MeV, Level 4: up to 700keV

sh_delay = 80

special_channel = 1

channels = range(0, 127)

ignore_channels = [9, 13, 24, 30, 102, 117]

enable_all_channel_readout = False
enable_8_neighbor_readout = False
enable_4_neighbor_readout = False


# systemSetupTriggerMode -------------------------

# System setup for trigger mode.
# This function will set necessary ASIC and system configuration for trigger mode.
# -------------------------------------------------
# input[0]: channels, array of channels to enable.
# input[1]: special channel, special channel id.
# input[2]: ignore_channels, channels to skip.
# input[3]: readout_enable_asics, array of asic IDs to enable for readout (0, 1, 2, 3).
# input[4]: enable_all_channel_readout, enables all channel readout.
# input[5]: enable_4_neighbor_readout, enables 4 neighbor readout.
# input[6]: enable_8_neighbor_readout, enables 8 neighbor readout.
# input[7]: gain_level, Level 1: up to 9MeV, Level 2: up to 7MeV, Level 3: up to 3MeV, Level 4: up to 700keV
# input[8]: sh_delay, Sample and hold delay.
# output: None.
# -------------------------------------------------
def systemSetupTriggerMode(channels=None, special_channel=0, ignore_channels=[9], readout_enable_asics=[],
                           enable_all_channel_readout=0, enable_4_neighbor_readout=0, enable_8_neighbor_readout=0,
                           gain_level=4, sh_delay=80):
    print('Configuring system for trigger mode...')
    default_file_path = os.getcwd() + '\\conf\\GDS-100\\IDE3422_register_definitions.json'

    # Initiate all ASICs in use with default values:
    for i in range(len(readout_enable_asics)):
        print('Initializing ASIC ' + str(readout_enable_asics[i]))

        readoutEnable(readout_enable_asics[i])
        time.sleep(1)
        tb.writeSysReg(addr_mares, readout_enable_asics[i])
        time.sleep(1)
        tb.readAsicConfigValuesFromFile(default_file_path, readout_enable_asics[i], 0)
        time.sleep(.5)
        tb.writeReadAsicConfig(readout_enable_asics[i])
        time.sleep(1)

    readoutEnableList(readout_enable_asics)
    time.sleep(0.5)

    # Set readout mode
    ro_all = 0
    if enable_all_channel_readout:
        ro_all = 1

    ro8 = 0
    ro4b = 1
    if enable_4_neighbor_readout:
        ro4b = 0

    if enable_8_neighbor_readout:
        ro8 = 1
        ro4b = 0

    # Default as level 4-high gain
    gain_c3b = 1
    gain_c9 = 0

    if gain_level == 1:
        gain_c3b = 0
        gain_c9 = 1
    elif gain_level == 2:
        gain_c9 = 1
    elif gain_level == 3:
        gain_c3b = 0

    for i in range(len(readout_enable_asics)):

        asic_id = readout_enable_asics[i]

        # Disable forced readout
        tb.writeSysReg(addr_forced_en, 0)

        # Disable cal test
        tb.setAsicConfigBitFieldByAddr(bitaddr_test_on, 0, asic_id)

        triggerAllNormal(1, asic_id)
        triggerAllSpecial(1, asic_id)

        # Add customized settings.
        tb.setAsicConfigBitFieldByAddr(bitaddr_ro_all, ro_all, asic_id)
        tb.setAsicConfigBitFieldByAddr(bitaddr_test_on, 0, asic_id)
        tb.setAsicConfigBitFieldByAddr(bitaddr_gain_c3b, gain_c3b, asic_id)
        tb.setAsicConfigBitFieldByAddr(bitaddr_gain_c9, gain_c9, asic_id)
        mon_d_out = 0
        tb.setAsicConfigBitFieldByAddr(bitaddr_mon_d_out, mon_d_out, asic_id)
        tb.setAsicConfigBitFieldByAddr(bitaddr_ro8, ro8, asic_id)
        tb.setAsicConfigBitFieldByAddr(bitaddr_ro4b, ro4b, asic_id)
        readclk_b2 = 1
        tb.setAsicConfigBitFieldByAddr(bitaddr_readclk_b2, readclk_b2, asic_id)
        tb.setAsicConfigBitFieldByAddr(bitaddr_sh_delay, sh_delay, asic_id)

        for channel in channels:
            if channel in ignore_channels:
                continue
            #print("Enabling channel " + str(channel) + ' ASIC ID ' + str(asic_id))
            triggerEnableNormal(channel, asic_id)

        print("Readout is running on ASIC " + str(asic_id) + " with " + str(len(channels)) + " channels enabled.")

        # Enable forced readout for special channel
        enableForcedSpecial(special_channel, asic_id)
        time.sleep(1)

        tb.writeReadAsicConfig(asic_id)

        time.sleep(1)

    print("Readout is running on ASIC " + str(readout_enable_asics))


systemSetupTriggerMode(channels, special_channel, ignore_channels, readout_enable_asics,
                       enable_all_channel_readout, enable_4_neighbor_readout, enable_8_neighbor_readout, gain_level,
                       sh_delay)
