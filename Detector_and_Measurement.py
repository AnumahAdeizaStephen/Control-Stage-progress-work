import os
import sys
import time

sys.path.append(os.getcwd() + '\\scripts\\GDS-100\\')
from tb_product import *

stage_position = {'x': 0, 'y': 0}

def move_x(to_x):
    print('Moving in X to position {}...'.format(to_x))
    stage_position['x'] = to_x
    time.sleep(0.1)
    print('Reached X = {}'.format(to_x))

def move_y(to_y):
    print('Moving in Y to position {}...'.format(to_y))
    stage_position['y'] = to_y
    time.sleep(0.1)
    print('Reached Y = {}'.format(to_y))

def log_data(run_number, x, y, duration):
    timestamp = time.strftime("%Y-%m-%d__%H_%M_%S")
    filename = 'logs\\Testrun{}_x{}_y{}_{}.bin'.format(run_number, x, y, timestamp)
    tb.newDataLogFile(filename)
    tb.enableDataLogging(True)
    print('Detector On.')
    print('Started data recording at (x={}, y={}).'.format(x, y))
    time.sleep(duration)
    tb.enableDataLogging(False)
    print('Stopped data recording at (x={}, y={})'.format(x, y))
    print('Detector Off.')

def raster_scan(x_range, y_range, measurement_time=60, settle_time=20):
    run_number = 1
    for y in y_range:
        move_y(y)
        if y % 2 == 0:
            x_sequence = x_range
        else:
            x_sequence = reversed(x_range)
        for x in x_sequence:
            move_x(x)
            time.sleep(settle_time)
            log_data(run_number, x, y, measurement_time)
            time.sleep(settle_time)
            run_number += 1
    tb.writeSysReg(addr_cal_exe, 0)
    print('Readout stopped.')

def main():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    x_range = range(0, 3)
    y_range = range(0, 3)
    tb.enableDataLogging(False)
    raster_scan(x_range, y_range, measurement_time=10, settle_time=10)

if __name__ == '__main__':
    main()