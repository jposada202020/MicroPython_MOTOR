# SPDX-FileCopyrightText: 2017 Scott Shawcroft for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT
"""
`servo`
================================================================================

MicroPython Helper for controlling PWM based servos


* Author(s): Scott Shawcroft, Jose D. Montoya


"""


class _BaseServo:
    """Shared base class that handles pulse output based on a value between 0 and 1.0

    :param pwm_out: PWM output object.
    :param int min_pulse: The minimum pulse length of the servo in microseconds.
    :param int max_pulse: The maximum pulse length of the servo in microseconds."""

    def __init__(self, pwm_out, *, min_pulse: int = 500, max_pulse: int = 2250) -> None:
        self._pwm_out = pwm_out
        self.set_pulse_width_range(min_pulse, max_pulse)

    def set_pulse_width_range(
        self, min_pulse: int = 750, max_pulse: int = 2250
    ) -> None:
        """Change min and max pulse widths."""
        self._min_duty = int((min_pulse * self._pwm_out.freq()) / 1000000 * 0xFFFF)
        max_duty = (max_pulse * self._pwm_out.freq()) / 1000000 * 0xFFFF
        self._duty_range = int(max_duty - self._min_duty)

    @property
    def fraction(self):
        """Pulse width expressed as fraction between 0.0 (`min_pulse`) and 1.0 (`max_pulse`).
        For conventional servos, corresponds to the servo position as a fraction
        of the actuation range. Is None when servo is disabled (pulsewidth of 0ms).
        """
        if self._pwm_out.duty_u16() == 0:  # Special case for disabled servos
            return None
        return (self._pwm_out.duty_u16() - self._min_duty) / self._duty_range

    @fraction.setter
    def fraction(self, value) -> None:
        if value is None:
            self._pwm_out.duty_u16(0)
            return
        if not 0.0 <= value <= 1.0:
            raise ValueError("Must be 0.0 to 1.0")
        duty_cycle = self._min_duty + int(value * self._duty_range)
        self._pwm_out.duty_u16(duty_cycle)


class Servo(_BaseServo):
    """Control the position of a servo.

       :param pwm_out: PWM output object.
       :param int actuation_range: The physical range of motion of the servo in degrees, \
           for the given ``min_pulse`` and ``max_pulse`` values.
       :param int min_pulse: The minimum pulse width of the servo in microseconds.
       :param int max_pulse: The maximum pulse width of the servo in microseconds.

       ``actuation_range`` is an exposed property and can be changed at any time:

        .. code-block:: python

          servo = Servo(pwm)
          servo.actuation_range = 135

       The specified pulse width range of a servo has historically been 1000-2000us,
       for a 90 degree range of motion. But nearly all modern servos have a 170-180
       degree range, and the pulse widths can go well out of the range to achieve this
       extended motion. The default values here of ``750`` and ``2250`` typically give
       135 degrees of motion. You can set ``actuation_range`` to correspond to the
       actual range of motion you observe with your given ``min_pulse`` and ``max_pulse``
       values.

       .. warning:: You can extend the pulse width above and below these limits to
         get a wider range of movement. But if you go too low or too high,
         the servo mechanism may hit the end stops, buzz, and draw extra current as it stalls.
         Test carefully to find the safe minimum and maximum.
    """

    def __init__(
        self,
        pwm_out,
        *,
        actuation_range: int = 180,
        min_pulse: int = 750,
        max_pulse: int = 2250
    ) -> None:
        super().__init__(pwm_out, min_pulse=min_pulse, max_pulse=max_pulse)
        self.actuation_range = actuation_range
        """The physical range of motion of the servo in degrees.

        :type: float
        """
        self._pwm = pwm_out

    @property
    def angle(self):
        """The servo angle in degrees. Must be in the range ``0`` to ``actuation_range``.
        Is None when servo is disabled."""
        if self.fraction is None:
            return None
        return self.actuation_range * self.fraction

    @angle.setter
    def angle(self, new_angle) -> None:
        if new_angle is None:  # disable the servo by sending 0 signal
            self.fraction = None
            return
        if new_angle < 0 or new_angle > self.actuation_range:
            raise ValueError("Angle out of range")
        self.fraction = new_angle / self.actuation_range
