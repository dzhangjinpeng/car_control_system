from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.motor_client import MockMotorClient


class MotorClientTargetTest(unittest.TestCase):
    def test_mock_tracks_drive_velocity_targets(self) -> None:
        motors = MockMotorClient()

        motors.control_vel(1, 1.25)

        self.assertAlmostEqual(motors.get_target_velocity(1), 1.25)
        self.assertAlmostEqual(motors.get_velocity(1), 1.25)

    def test_mock_tracks_steer_position_targets(self) -> None:
        motors = MockMotorClient()

        motors.control_pos_vel(6, 0.5, 2.0)

        self.assertAlmostEqual(motors.get_target_position(6), 0.5)
        self.assertAlmostEqual(motors.get_target_velocity(6), 2.0)


if __name__ == "__main__":
    unittest.main()
