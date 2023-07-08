# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

"""
Example adapted from
https://github.com/WoolseyWorkshop/Article-Driving-A-DC-Motor-With-CircuitPython/blob/main/motors.py
"""

from time import sleep
from machine import PWM, Pin
from micropython_motor import MOTOR

OP_DURATION = 2  # The operation duration in seconds

# Pin Mapping
drv_switch = Pin(11, Pin.OUT)  # Pin to enable/disable the DRV8833
drv8833_ain1 = PWM(Pin(9, Pin.OUT))
drv8833_ain1.freq(50)
drv8833_ain2 = PWM(Pin(10, Pin.OUT))
drv8833_ain2.freq(50)

"""The PWM enabled pin connected to the AIN1 (motor A control 1) pin of the
DRV8833 motor driver board.  Specifying a PWM frequency of less than 100 Hz
typically improves the low speed operation of brushed DC motors.
"""
motor_a = MOTOR(drv8833_ain1, drv8833_ain2)

drv_switch.on()

# Drive backwards at 50% throttle
motor_a.throttle = 1.0
sleep(OP_DURATION)

# Coast to a stop
motor_a.throttle = None
sleep(OP_DURATION)

# Drive backwards at 50% throttle
motor_a.throttle = -0.5
sleep(OP_DURATION)

# Brake to a stop
motor_a.throttle = 0
sleep(OP_DURATION)

drv_switch.off()
