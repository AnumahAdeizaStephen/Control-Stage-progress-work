# ===============================================
# Script: system_info.py ========================
# ===============================================

# Last updated: 2023-01-26
# Made by IDEAS

# ===============================================
# Description ===================================
# ===============================================

# This script runs through the system monitoring
# functions on the GDS-100.
#
# It reads the serial numbers and version
# information, and it performs voltage and
# temperature measurements. All readings are
# printed in the Python output. Large deviations
# in power rail voltage measurements are shown.
#
# The user can adjust the maximum allowed
# deviation of the measured voltages.

import os
import sys
import time

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
import tb_product

tb_product = reload(tb_product)


def printSystemInfo():
    # ===============================================
    # Settings ======================================
    # ===============================================
    deviation = 5  # Threshold for accepted power rail deviation (%)
    # ===============================================
    # Initialization ================================
    # ===============================================
    sn = 0
    fw_type = 0
    fw_ver = 0
    sys_num = 0
    mac = 0

    tb.readSysReg(tb_product.addr_sn)
    tb.readSysReg(tb_product.addr_fw_type)
    tb.readSysReg(tb_product.addr_fw_ver)
    tb.readSysReg(tb_product.addr_sys_num)
    tb.readSysReg(tb_product.addr_mac)
    tb.readSysReg(tb_product.addr_fpga_ver)
    tb.readSysReg(tb_product.addr_fw_date)

    tb.readSysReg(tb_product.addr_soc_temp)
    tb.readSysReg(tb_product.addr_mon_vi)
    tb.readSysReg(tb_product.addr_mon_fe22)
    tb.readSysReg(tb_product.addr_mon_vcc2v5)
    tb.readSysReg(tb_product.addr_cboard_temp)
    tb.readSysReg(tb_product.addr_mboard_temp)

    time.sleep(.1)

    tb.readSysReg(tb_product.addr_soc_temp)
    tb.readSysReg(tb_product.addr_mon_vi)
    tb.readSysReg(tb_product.addr_mon_fe22)
    tb.readSysReg(tb_product.addr_mon_vcc2v5)
    tb.readSysReg(tb_product.addr_cboard_temp)
    tb.readSysReg(tb_product.addr_mboard_temp)

    time.sleep(.1)

    tb.readSysReg(tb_product.addr_soc_temp)
    tb.readSysReg(tb_product.addr_mon_vi)
    tb.readSysReg(tb_product.addr_mon_fe22)
    tb.readSysReg(tb_product.addr_mon_vcc2v5)
    tb.readSysReg(tb_product.addr_cboard_temp)
    tb.readSysReg(tb_product.addr_mboard_temp)

    time.sleep(.1)

    tb.readSysReg(tb_product.addr_soc_temp)
    tb.readSysReg(tb_product.addr_mon_vi)
    tb.readSysReg(tb_product.addr_mon_fe22)
    tb.readSysReg(tb_product.addr_mon_vcc2v5)
    tb.readSysReg(tb_product.addr_cboard_temp)
    tb.readSysReg(tb_product.addr_mboard_temp)

    time.sleep(.1)

    tb.readSysReg(tb_product.addr_soc_temp)
    tb.readSysReg(tb_product.addr_mon_vi)
    tb.readSysReg(tb_product.addr_mon_fe22)
    tb.readSysReg(tb_product.addr_mon_vcc2v5)
    tb.readSysReg(tb_product.addr_cboard_temp)
    tb.readSysReg(tb_product.addr_mboard_temp)

    time.sleep(.1)

    tb.readSysReg(tb_product.addr_soc_temp)
    tb.readSysReg(tb_product.addr_mon_vi)
    tb.readSysReg(tb_product.addr_mon_fe22)
    tb.readSysReg(tb_product.addr_mon_vcc2v5)
    tb.readSysReg(tb_product.addr_cboard_temp)
    tb.readSysReg(tb_product.addr_mboard_temp)

    time.sleep(.1)

    sn = tb.getSysRegValue(tb_product.addr_sn)
    fw_type = tb.getSysRegValue(tb_product.addr_fw_type)
    fw_ver = tb.getSysRegValue(tb_product.addr_fw_ver)
    sys_num = tb.getSysRegValue(tb_product.addr_sys_num)
    mac = tb.getSysRegValue(tb_product.addr_mac)
    fpga_ver = tb.getSysRegValue(tb_product.addr_fpga_ver)
    fw_date = tb.getSysRegValue(tb_product.addr_fw_date)

    time.sleep(.1)

    deviation_occurred = False

    # ===============================================
    # Calculation ===================================
    # ===============================================

    cboard_temp = (tb.getSysRegValue(tb_product.addr_cboard_temp) >> 4) * 0.0625
    mboard_temp = (tb.getSysRegValue(tb_product.addr_mboard_temp) >> 4) * 0.0625
    soc_temp = (tb.getSysRegValue(tb_product.addr_soc_temp)) / 10.0

    mon_vin = (tb.getSysRegValue(tb_product.addr_mon_vi) / 4096.0) * (1 / 0.0769)
    mon_fe22 = (tb.getSysRegValue(tb_product.addr_mon_fe22) / 4096.0) * (1 / 0.2326)
    mon_vcc2v5 = (tb.getSysRegValue(tb_product.addr_mon_vcc2v5) / 4096.0) * (1 / 0.2326)

    deviation_vin = abs(mon_vin - 12.0) / 12.0
    deviation_fe22 = abs(mon_fe22 - 2.2) / 2.2
    deviation_vcc2v5 = abs(mon_vcc2v5 - 2.5) / 2.5

    # ===============================================
    # Presentation ==================================
    # ===============================================

    print('-')
    print('Serial number: ' + str(sn))
    print('Firmware type: %X' % fw_type)
    print('Firmware version: ' + str(fw_ver))
    print('FW date: ' + str(fw_date))
    print('FPGA version: ' + str(fpga_ver))
    print('System number: ' + str(sys_num))
    print('MAC address: %X' % mac)

    print('-')
    print('Temperature measurements:')
    print('Controller board: ' + str(round(cboard_temp, 1)) + ' ' + chr(176) + 'C')
    print('Motherboard: ' + str(round(mboard_temp, 1)) + ' ' + chr(176) + 'C')
    print('SoC: ' + str(round(soc_temp, 1)) + ' ' + chr(176) + 'C')
    print('-')
    print('Power rail measurements:')
    print('V-INPUT: ' + str(round(mon_vin, 2)) + ' V')
    print('V-FE22: ' + str(round(mon_fe22, 2)) + ' V')
    print('VCC2V5: ' + str(round(mon_vcc2v5, 2)) + ' V')

    if deviation_vin > deviation / 100.0:
        print('WARNING: V-INPUT off by ' + str(round((deviation_vin * 100), 2)) + ' percent.')
        deviation_occurred = True

    if deviation_fe22 > deviation / 100.0:
        print('WARNING: V-FE22 off by ' + str(round((deviation_fe22 * 100), 2)) + ' percent.')
        deviation_occurred = True

    if deviation_vcc2v5 > deviation / 100.0:
        print('WARNING: VCC2V5 off by ' + str(round((deviation_vcc2v5 * 100), 2)) + ' percent.')
        deviation_occurred = True

    if not deviation_occurred:
        print('Power rails voltages are OK. All rails within ' + str(deviation) + ' percent of target.')


printSystemInfo()
