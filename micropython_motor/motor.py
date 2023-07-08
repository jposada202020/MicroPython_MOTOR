# SPDX-FileCopyrightText: 2021 Scott Shawcroft for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT
"""
`motor`
================================================================================

MicroPython Helper for controlling PWM based motors


* Author(s): Scott Shawcroft, Jose D. Montoya


"""

FAST_DECAY = 0
"""Recirculation current fast decay mode (coasting)"""

SLOW_DECAY = 1
"""Recirculation current slow decay mode (braking)"""


class MOTOR:
    """DC motor driver. ``positive_pwm`` and ``negative_pwm`` can be swapped if the motor runs in
    the opposite direction from what was expected for "forwards".

    Motor controller recirculation current decay mode is selectable and defaults to
    ``motor.FAST_DECAY`` (coasting). ``motor.SLOW_DECAY`` is recommended to improve spin
    threshold, speed-to-throttle linearity, and PWM frequency sensitivity.

    Decay mode settings only effect the operational performance of controller chips such
    as the DRV8833, DRV8871, and TB6612. Either decay mode setting is compatible
    with discrete h-bridge controller circuitry such as the L9110H and L293D; operational
    performance is not altered.

    :param positive_pwm: The motor input that causes the motor to spin forwards
      when high and the other is low.
    :param negative_pwm: The motor input that causes the motor to spin backwards
      when high and the other is low."""

    def __init__(self, positive_pwm, negative_pwm) -> None:
        self._positive = positive_pwm
        self._negative = negative_pwm
        self._throttle = None
        self._decay_mode = FAST_DECAY

    @property
    def throttle(self):
        """Motor speed, ranging from -1.0 (full speed reverse) to 1.0 (full speed forward),
        or ``None`` (controller off).
        If ``None``, both PWMs are turned full off. If ``0.0``, both PWMs are turned full on.
        """
        return self._throttle

    @throttle.setter
    def throttle(self, value) -> None:
        if value is not None and (value > 1.0 or value < -1.0):
            raise ValueError("Throttle must be None or between -1.0 and +1.0")
        self._throttle = value
        if value is None:  # Turn off motor controller (high-Z)
            self._positive.duty_u16(0)
            self._negative.duty_u16(0)
        elif value == 0:  # Brake motor (low-Z)
            self._positive.duty_u16(0xFFFF)
            self._negative.duty_u16(0xFFFF)
        else:
            duty_cycle = int(0xFFFF * abs(value))
            if self._decay_mode == SLOW_DECAY:  # Slow Decay (Braking) Mode
                if value < 0:
                    self._positive.duty_u16(0xFFFF - duty_cycle)
                    self._negative.duty_u16(0xFFFF)
                else:
                    self._positive.duty_u16(0xFFFF)
                    self._negative.duty_u16(0xFFFF - duty_cycle)
            else:  # Default Fast Decay (Coasting) Mode
                if value < 0:
                    self._positive.duty_u16(0)
                    self._negative.duty_u16(duty_cycle)
                else:
                    self._positive.duty_u16(duty_cycle)
                    self._negative.duty_u16(0)

    @property
    def decay_mode(self) -> int:
        """Motor controller recirculation current decay mode. A value of ``motor.FAST_DECAY``
        sets the motor controller to the default fast recirculation current decay mode
        (coasting); ``motor.SLOW_DECAY`` sets slow decay (braking) mode."""
        return self._decay_mode

    @decay_mode.setter
    def decay_mode(self, mode: int = FAST_DECAY) -> None:
        if mode in (FAST_DECAY, SLOW_DECAY):
            self._decay_mode = mode
        else:
            raise ValueError(
                "Decay mode value must be either motor.FAST_DECAY or motor.SLOW_DECAY"
            )

    def __enter__(self):
        return self

    def __exit__(
        self,
        exception_type,
        exception_value,
        traceback,
    ) -> None:
        self.throttle = None
