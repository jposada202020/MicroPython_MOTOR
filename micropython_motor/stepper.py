# SPDX-FileCopyrightText: 2017 Scott Shawcroft  for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

"""
`stepper`
====================================================

MicroPython Helper for controlling stepper motors with microstepping support.


* Author(s): Tony DiCola, Scott Shawcroft, Jose D. Montoya
"""

import math
from micropython import const


# Constants that specify the direction and style of steps.
FORWARD = const(1)  # Step forward
BACKWARD = const(2)  # Step backward
SINGLE = const(1)  # Step so that each step only activates a single coil
# Step so that each step only activates two coils to produce more torque
DOUBLE = const(2)
# Step half a step to alternate between single coil and double coil steps
INTERLEAVE = const(3)
# Step a fraction of a step by partially activating two neighboring coils
# Step size is determined by ``microsteps`` constructor argument.
MICROSTEP = const(4)

_SINGLE_STEPS = bytes([0b0010, 0b0100, 0b0001, 0b1000])
_DOUBLE_STEPS = bytes([0b1010, 0b0110, 0b0101, 0b1001])
_INTERLEAVE_STEPS = bytes(
    [0b1010, 0b0010, 0b0110, 0b0100, 0b0101, 0b0001, 0b1001, 0b1000]
)


class StepperMotor:
    """A bipolar stepper motor or four coil unipolar motor. The use of microstepping requires
    pins that can output PWM. For non-microstepping, can set microsteps to None and use
    digital out pins.


    :param ain1: `machine.PWM` or `machine.Pin`-compatible output connected to the driver for
      the first coil (unipolar) or first input to first coil (bipolar).
    :param  ain2: `machine.PWM` or `machine.Pin`-compatible output connected to the driver for
      the third coil (unipolar) or second input to first coil (bipolar).
    :param bin1: `machine.PWM` or `machine.Pin`-compatible output connected to the driver for
      the second coil (unipolar) or second input to second coil (bipolar).
    :param bin2: `machine.PWM` or `machine.Pin`-compatible output connected to the driver for
      the fourth coil (unipolar) or second input to second coil (bipolar).
    :param int microsteps: Number of microsteps between full steps. Must be at least 2 and even.

    """

    def __init__(self, ain1, ain2, bin1, bin2, *, microsteps=16) -> None:
        if microsteps is None:
            # Digital IO Pins
            self._steps = None
            self._coil = (ain1, ain2, bin1, bin2)
        else:
            # PWM Pins set a safe pwm freq for each output
            self._coil = (ain2, bin1, ain1, bin2)
            for i in range(4):
                if self._coil[i].freq() < 1500:
                    try:
                        self._coil[i].frequency = 2000
                    except AttributeError as err:
                        raise ValueError(
                            "PWMOut outputs must either be set to at least "
                            "1500 Hz or allow variable frequency."
                        ) from err
            if microsteps < 2:
                raise ValueError("Microsteps must be at least 2")
            if microsteps % 2 == 1:
                raise ValueError("Microsteps must be even")
            self._curve = [
                int(round(0xFFFF * math.sin(math.pi / (2 * microsteps) * i)))
                for i in range(microsteps + 1)
            ]
        self._current_microstep = 0
        self._microsteps = microsteps
        self._update_coils()

    def _update_coils(self, *, microstepping: bool = False) -> None:
        if self._microsteps is None:
            # Digital IO Pins Get coil activation sequence
            if self._steps is None:
                steps = 0b0000
            else:
                steps = self._steps[self._current_microstep % len(self._steps)]
            # Energize coils as appropriate:
            for i, coil in enumerate(self._coil):
                coil.value((steps >> i) & 0x01)
        else:
            # PWM Pins
            duty_cycles = [0, 0, 0, 0]
            trailing_coil = (self._current_microstep // self._microsteps) % 4
            leading_coil = (trailing_coil + 1) % 4
            microstep = self._current_microstep % self._microsteps
            duty_cycles[leading_coil] = self._curve[microstep]
            duty_cycles[trailing_coil] = self._curve[self._microsteps - microstep]

            # This ensures DOUBLE steps use full torque. Without it, we'd use
            #  partial torque from the microstepping curve (0xb504).
            if not microstepping and (
                duty_cycles[leading_coil] == duty_cycles[trailing_coil]
                and duty_cycles[leading_coil] > 0
            ):
                duty_cycles[leading_coil] = 0xFFFF
                duty_cycles[trailing_coil] = 0xFFFF

            # Energize coils as appropriate:
            for i in range(4):
                self._coil[i].duty_u16(duty_cycles[i])

    def release(self) -> None:
        """Releases all the coils so the motor can free spin, also won't use any power"""
        # De-energize coils:
        for coil in self._coil:
            if self._microsteps is None:
                coil.value(0)
            else:
                coil.duty_u16(0)

    def onestep(self, *, direction: int = FORWARD, style: int = SINGLE) -> None:
        """Performs one step of a particular style. The actual rotation amount will vary by style.
        :const:`SINGLE` and :const:`DOUBLE` will normal cause a full step rotation.
        :const:`INTERLEAVE` will normally do a half step rotation. :const:`MICROSTEP`
        will perform the smallest configured step.

        When step styles are mixed, subsequent :const:`SINGLE`, :const:`DOUBLE` or
        :const:`INTERLEAVE` steps may be less than normal in order to align to the
        desired style's pattern.

        :param int direction: Either :const:`FORWARD` or :const:`BACKWARD`
        :param int style: :const:`SINGLE`, :const:`DOUBLE`, :const:`INTERLEAVE`

        """
        if self._microsteps is None:
            # Digital IO Pins
            step_size = 1
            if style == SINGLE:
                self._steps = _SINGLE_STEPS
            elif style == DOUBLE:
                self._steps = _DOUBLE_STEPS
            elif style == INTERLEAVE:
                self._steps = _INTERLEAVE_STEPS
            else:
                raise ValueError("Unsupported step style.")
        else:
            # PWM Pins Adjust current steps based on the direction and type of step.
            step_size = 0
            if style == MICROSTEP:
                step_size = 1
            else:
                half_step = self._microsteps // 2
                full_step = self._microsteps
                # Its possible the previous steps were MICROSTEPS so first align
                #  with the interleave pattern.
                additional_microsteps = self._current_microstep % half_step
                if additional_microsteps != 0:
                    # We set _current_microstep directly because our step size varies
                    # depending on the direction.
                    if direction == FORWARD:
                        self._current_microstep += half_step - additional_microsteps
                    else:
                        self._current_microstep -= additional_microsteps
                    step_size = 0
                elif style == INTERLEAVE:
                    step_size = half_step

                current_interleave = self._current_microstep // half_step
                if (style == SINGLE and current_interleave % 2 == 1) or (
                    style == DOUBLE and current_interleave % 2 == 0
                ):
                    step_size = half_step
                elif style in (SINGLE, DOUBLE):
                    step_size = full_step

        if direction == FORWARD:
            self._current_microstep += step_size
        else:
            self._current_microstep -= step_size

        # Now that we know our target microstep we can determine how to energize the four coils.
        self._update_coils(microstepping=style == MICROSTEP)

        return self._current_microstep
