#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 11

@author: Tao Liu / Olivier Chanrion / DTU Space

Inspired from Metavision SDK get started
https://github.com/atdtu/openeb/blob/main/sdk/modules/core/python/samples/metavision_sdk_get_started/metavision_sdk_get_started_v2.py
Copyright (c) Prophesee S.A. - see LICENSE_OPEN.txt
"""

import sys
sys.path.append("/usr/lib/python3/dist-packages/")

import numpy as np
from metavision_core.event_io import EventsIterator
import matplotlib.pyplot as plt

def event_counts(raw_file_path, accumulation_time_us):
    events_iterator = EventsIterator(raw_file_path, delta_t=accumulation_time_us)

    timestamps = []
    event_counts = []

    for evs in events_iterator:
        if len(evs) == 0:
            continue

        t_start = evs['t'][0]
        num_events = np.count_nonzero(evs['p'] == 1)  # ON events

        timestamps.append(t_start / 1e3)  # milliseconds
        event_counts.append(num_events)

    return np.array(timestamps), np.array(event_counts)

master_file = "master_4110040565_20260211_095621_284736.raw"
slave_file  = "slave_4110040580_20260211_095621_284736.raw"

accumulation_time_us = 1000  # in us

t_master, c_master = event_counts(master_file, accumulation_time_us)
t_slave,  c_slave  = event_counts(slave_file, accumulation_time_us)

fig, ax1 = plt.subplots(figsize=(12, 6))

line1, = ax1.plot(t_master, c_master, linewidth=1, color='red', label="Master")
ax1.set_xlabel("Time (ms)")
ax1.set_ylabel("Master")
ax1.tick_params(axis='y')
ax1.grid(True)

ax2 = ax1.twinx()
line2, = ax2.plot(t_slave, c_slave, linewidth=1, linestyle='--', alpha=0.8, color='blue', label="Slave")
ax2.set_ylabel("Slave")
ax2.tick_params(axis='y')

ax1.set_xlim(0, 100)
ax1.set_ylim(bottom=0)
ax2.set_ylim(bottom=0)

lines = [line1, line2]
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc="upper right")

plt.title(f"Input Source: 100Hz Sine Wave (LED) - Master vs Slave ON Event Compare, accumulation time {accumulation_time_us} us")
plt.tight_layout()
plt.show()