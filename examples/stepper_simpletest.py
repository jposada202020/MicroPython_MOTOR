# SPDX-FileCopyrightText: 2021 jedgarpark for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

"""Example adapted from
https://learn.adafruit.com/use-dc-stepper-servo-motor-solenoid-rp2040-pico/stepper-motor"""

# Hardware setup:
#   Stepper motor via DRV8833 driver breakout on GP21, GP20, GP19, GP18
#   external power supply
#   DRV8833 Enabled on GP16

import time
from machine import Pin
from micropython_motor import stepper

print("Stepper test")


mode = -1

# Mode button setup
drv_switch = Pin(16, Pin.OUT)
drv_switch.on()

# Stepper motor setup
DELAY = 0.006  # fastest is ~ 0.004, 0.01 is still very smooth, gets steppy after that
STEPS = 513  # this is a full 360º
coils = (Pin(21, Pin.OUT), Pin(20, Pin.OUT), Pin(19, Pin.OUT), Pin(18, Pin.OUT))


stepper_motor = stepper.StepperMotor(
    coils[0], coils[1], coils[2], coils[3], microsteps=None
)


def stepper_fwd():
    print("stepper forward")
    for _ in range(STEPS):
        stepper_motor.onestep(direction=stepper.FORWARD)
        time.sleep(DELAY)
    stepper_motor.release()


def stepper_back():
    print("stepper backward")
    for _ in range(STEPS):
        stepper_motor.onestep(direction=stepper.BACKWARD)
        time.sleep(DELAY)
    stepper_motor.release()


def run_test(testnum):
    if testnum == 0:
        stepper_fwd()
    elif testnum == 1:
        stepper_back()


while True:
    mode = (mode + 1) % 2
    print("switch to mode %d" % (mode))
    print()
    time.sleep(0.8)  # big debounce
    run_test(mode)
