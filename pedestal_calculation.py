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
from datetime import datetime
import numpy as np

sys.path.append(os.getcwd() + '\\logs\\')
sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')

from tb_product import *
import tb_product as tb_product
import pedestal_helper_functions as phf

reload(tb_product)
reload(phf)


# enablePedestalCorrection -------------------------

# This funciton will use forced readout to readout a specified number of pedestal readouts
# and store them in a file, the readouts are read and pedestals for each cell in all channels 
# are calculated and loaded into the pedestal ram. Lastly it will enable pedestal correction. 
# Note: Pedestals will change based on VFP, VFP0 settings, so it is always recommended to recalculate 
# pedestals when changed.
# -------------------------------------------------
# input[0]: asic_id, which asic to program [0,1,2,3]. 
# input[1]: nr_readouts, number of readouts to trigger from each channel. 
# -------------------------------------------------

def enablePedestalCorrection(asic_id = 0, nr_readouts = 10):

    sh_delay = 80
    forced_start_column = 1
    
    # Disable pedestal correction
    tb.writeSysReg(addr_pedram_enable, 1)
    
    current_time = datetime.now()
    time_str = current_time.strftime("%Y-%m-%d_%H-%M-%S")  # Format: YYYY-MM-DD_HH-MM-SS
    
    cwd = os.getcwd()
    path_pedestal = os.path.join(cwd, 'logs', 'Pedestals')
    path_pedestal_file = os.path.join(cwd, 'logs', 'Pedestals', 'pedestals_AS%s_%s.bin' % (asic_id, time_str))
    # Use forced readout to collect baseline data. 
    phf.forced_readout_pedestals(asic_id, path_pedestal_file, pulse_num = nr_readouts, sh_delay = sh_delay, start_col = forced_start_column)
  
    latest_pedestal_file = phf.return_latest_file(path_pedestal)

    print('Loading pedestal file: '+ latest_pedestal_file)
    print('Calculating pedestals in progress..')
    # Calculate pedestals for each cell for all channels.    
    calc_pedestals = phf.load_pedestals_from_bin_file(latest_pedestal_file, forced_start_column = forced_start_column, sh_delay = sh_delay)
    print('Finish calculating pedestals')
    # Write pedestal to pedram    
    phf.write_pedestals_into_ped_ram(calc_pedestals, asic_id = asic_id, anode = True)
    print('Pedestals loaded and ready')
    # Enable pedestal correction
    tb.writeSysReg(addr_pedram_enable, 1)

asic_id = 0
nr_readouts = 10

enablePedestalCorrection(asic_id, nr_readouts)
