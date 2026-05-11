from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.config import HardwareConfig
from scripts.calibrate_hardware import validate_hardware_config


class HardwareCalibrationTest(unittest.TestCase):
    def test_valid_config_has_no_issues(self) -> None:
        hardware = HardwareConfig(
            serial_number="sn",
            nom_baud=1000000,
            dat_baud=5000000,
            bridge_library="bridge/cpp/build/libdm_bridge.so",
            motor_ids=[1, 2, 3, 4, 5, 6, 7, 8],
            drive_motor_ids=[1, 2, 3, 4],
            steer_motor_ids=[5, 6, 7, 8],
            inverted_drive_motor_ids=[2, 3],
            gear_ratio=3.0,
            wheel_radius=0.0855,
            wheelbase=0.5,
            track_width=0.4,
            drive_motor_roles={"rear_right": 1, "rear_left": 2, "front_left": 3, "front_right": 4},
            steer_motor_roles={"rear_left": 5, "front_left": 6, "front_right": 7, "rear_right": 8},
        )

        self.assertEqual(validate_hardware_config(hardware), [])

    def test_invalid_config_reports_issues(self) -> None:
        hardware = HardwareConfig(
            serial_number="sn",
            nom_baud=1000000,
            dat_baud=5000000,
            bridge_library="bridge/cpp/build/libdm_bridge.so",
            motor_ids=[1, 1, 3, 4],
            drive_motor_ids=[1, 2],
            steer_motor_ids=[3, 4],
            inverted_drive_motor_ids=[3],
            gear_ratio=0.0,
            wheel_radius=-1.0,
            wheelbase=0.0,
            track_width=-1.0,
            drive_motor_roles={"rear_right": 1, "rear_left": 2, "front_left": 3, "front_right": 4},
            steer_motor_roles={"rear_left": 3, "front_left": 4, "front_right": 5, "rear_right": 6},
        )

        issues = validate_hardware_config(hardware)

        self.assertTrue(issues)
        self.assertIn("motor_ids 有重复", issues)
        self.assertIn("gear_ratio 必须大于 0", issues)


if __name__ == "__main__":
    unittest.main()
