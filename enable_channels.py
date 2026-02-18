# ===============================================
# Script: enable_channels.py ==================
# ===============================================

# Last updated: 2023-01-26
# Made by IDEAS

# ===============================================
# Description ===================================
# ===============================================

# This file include functions that helps enable
# and disable channels during readout.

# ===============================================
# Initialization ================================
# ===============================================

import os
import sys

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *


# enableNormalChannels -----------------------------------------

# Enables chosen normal and special channels for triggering and 
# programs the ASIC with the new configuration. To enable all 
# channels, set enable_all true. Channels added to the 
# do_not_enable array will be ignored, even in enable all mode. 
# -------------------------------------------------
# input[0]: asic_id [0,1,2,3]
# input[1]: channels, array with channels to enable.
# input[2]: special_channel_nr, [0,1] (Note: There should always be one special channel enabled)
# input[3]: enable_all, enable all channels, [True, False]
# input[4]: ignore, array with channels to ignore.
# Output: None.
# -------------------------------------------------
def enableNormalChannels(asic_id, channels=None, special_channel_nr=None, enable_all=False, ignore=None):
    if special_channel_nr is not None:
        # Disable both special.
        triggerAllSpecial(1, asic_id)
        # Disable forced readout both special channels.
        forcedAllSpecial(0, asic_id)
        # Enable specified special channel.
        enableForcedSpecial(special_channel_nr, asic_id)

    # Disable all channels. 
    triggerAllNormal(1, asic_id)

    time.sleep(.5)

    if enable_all:
        channels = range(0, 127)

    enabled_cnt = 0
    for channel in channels:
        if channel in ignore:
            continue
        print("Enabling channel " + str(channel))
        triggerEnableNormal(channel, asic_id)
        enabled_cnt += 1

    time.sleep(.5)

    tb.writeReadAsicConfig(asic_id)

    time.sleep(2)

    print("Readout is running with " + str(enabled_cnt) + " channels enabled.")


enableNormalChannels(0, enable_all=True, ignore=[9], special_channel_nr=0)
