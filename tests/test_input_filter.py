from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.config import load_control_config
from car_control.input_filter import InputSmoother
from car_control.mapping import apply_drive_direction, turn_speed_scale
from car_control.state import DRIVE_DIRECTION_FORWARD_ONLY, DRIVE_DIRECTION_REVERSE_ONLY
from car_control.types import DriverInput


class InputSmootherTest(unittest.TestCase):
    def test_buttons_are_not_filtered(self) -> None:
        smoother = InputSmoother(load_control_config())
        result = smoother.apply(DriverInput(left_y=-1.0, mode_button=True, steering_lock_button=True))

        self.assertTrue(result.mode_button)
        self.assertTrue(result.steering_lock_button)

    def test_axes_move_toward_target_gradually(self) -> None:
        control = load_control_config()
        smoother = InputSmoother(control)

        first = smoother.apply(DriverInput(left_y=-1.0, left_x=1.0))
        second = smoother.apply(DriverInput(left_y=-1.0, left_x=1.0))

        self.assertLess(abs(first.left_y), 1.0)
        self.assertLess(abs(first.left_x), 1.0)
        self.assertGreater(abs(second.left_y), abs(first.left_y))
        self.assertGreater(abs(second.left_x), abs(first.left_x))

    def test_turn_speed_scale_drops_when_turning_harder(self) -> None:
        self.assertAlmostEqual(turn_speed_scale(0.0, 0.6, 1.5), 1.0)
        self.assertLess(turn_speed_scale(0.5, 0.6, 1.5), 1.0)
        self.assertAlmostEqual(turn_speed_scale(1.0, 0.6, 1.5), 0.6)

    def test_drive_direction_lock_changes_only_velocity_sign(self) -> None:
        self.assertEqual(apply_drive_direction(-0.5, DRIVE_DIRECTION_FORWARD_ONLY), 0.5)
        self.assertEqual(apply_drive_direction(0.5, DRIVE_DIRECTION_REVERSE_ONLY), -0.5)


if __name__ == "__main__":
    unittest.main()
