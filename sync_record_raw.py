#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 20 2026

@author: Tao Liu / Olivier Chanrion / DTU Space

Inspired from Metavision Sync Sample use python API for synchronizing two event-based cameras
https://github.com/prophesee-ai/openeb/blob/main/sdk/modules/core/python/samples/metavision_sync/metavision_sync.py
Copyright (c) Prophesee S.A. - see LICENSE_OPEN.txt
"""

import argparse
import sys
sys.path.append("/usr/lib/python3/dist-packages/")

import os
import time
import threading

from datetime import datetime
from cam_tools.biases import get_biases_from_file
from metavision_hal import DeviceDiscovery


def parse_args():
    parser = argparse.ArgumentParser(description='Metavision camera synchronization',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--master",  default="4110040565",
                        help="Serial number of MASTER camera") 
    parser.add_argument("--slave", default="4110040580",
                        help="Serial number of SLAVE camera")
    parser.add_argument("-b", "--bias-file", dest="bias_file", default="biases.bias", 
                        help="Apply bias settings on both cameras")
    return parser.parse_args()


def set_sync_mode(device, mode):
    i_sync = device.get_i_camera_synchronization()
    if not i_sync:
        raise RuntimeError("Camera does not support synchronization")

    if mode == "master":
        i_sync.set_mode_master()
    else:
        i_sync.set_mode_slave()

def apply_biases(device, biases, name="device"):
    i_ll_biases = device.get_i_ll_biases()
    if i_ll_biases is None:
        print(f"[{name}] Warning: no I_LL_Biases facility")
        return
    for k, v in biases.items():
        i_ll_biases.set(k, v)
    print(f"[{name}] Applied biases")

def record_stream(stream, stop_event):
    while not stop_event.is_set():
        stream.wait_next_buffer()
        stream.get_latest_raw_data()

def main():
    args = parse_args()

    print("Opening slave camera first...")
    slave = DeviceDiscovery.open(args.slave)
    if not slave:
        raise RuntimeError("Failed to open slave camera")
        
    set_sync_mode(slave, "slave")
    print("Slave set to SLAVE mode.")

    print("Opening master camera...")
    master = DeviceDiscovery.open(args.master)
    if not master:
        raise RuntimeError("Failed to open master camera")

    set_sync_mode(master, "master")
    print("Master set to MASTER mode.")

    if args.bias_file:
        biases = get_biases_from_file(args.bias_file)
        apply_biases(slave, biases, "SLAVE")
        apply_biases(master, biases, "MASTER")
        
    # Streams
    slave_stream = slave.get_i_events_stream()
    master_stream = master.get_i_events_stream()

    slave_stream.start()
    time.sleep(1)
    master_stream.start()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    slave_id = slave.get_i_hw_identification().get_serial()
    master_id = master.get_i_hw_identification().get_serial()

    slave_path = f"slave_{slave_id}_{ts}.raw"
    master_path = f"master_{master_id}_{ts}.raw"

    slave_stream.log_raw_data(slave_path)
    master_stream.log_raw_data(master_path)

    print("\nRecording:")
    print(" Slave :", slave_path)
    print(" Master:", master_path)
    print("Ctrl+C to stop\n")
    
    stop_event = threading.Event()

    slave_thread = threading.Thread(
        target=record_stream,
        args=(slave_stream, stop_event),
        daemon=True
    )

    master_thread = threading.Thread(
        target=record_stream,
        args=(master_stream, stop_event),
        daemon=True
    )

    slave_thread.start()
    master_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

    slave_stream.stop()
    master_stream.stop()

    slave_thread.join(timeout=2)
    master_thread.join(timeout=2)

    slave_stream.stop_log_raw_data()
    master_stream.stop_log_raw_data()

    print("Finished")


if __name__ == "__main__":
    main()
