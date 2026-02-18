# ===============================================
# Script: HV_control.py ==================
# ===============================================

# Last updated: 2023-01-04
# Made by IDEAS

# ===============================================
# Description ===================================
# ===============================================

# Control the high voltage setting. 

# ===============================================
# Initialization ================================
# ===============================================

import os
import sys

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *

# See conversion table in the GDS-100 User Manual to find correct LSB->HV 

voltage_dac =   0

setHV(voltage_dac, step=50, step_delay=.5)
