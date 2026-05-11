from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.config import HardwareConfig
from car_control.motor_client import MockMotorClient
from scripts.calibrate_hardware import verify_steer_zero


class SteerZeroVerificationTest(unittest.TestCase):
    def _hardware(self) -> HardwareConfig:
        return HardwareConfig(
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

    def test_steer_zero_verification_passes_when_close_to_center(self) -> None:
        hardware = self._hardware()
        motors = MockMotorClient()
        motors.positions[5] = 0.0
        motors.positions[6] = 0.0
        motors.positions[7] = 0.0
        motors.positions[8] = 0.0

        ok, records = verify_steer_zero(hardware, motors, tolerance_deg=5.0)

        self.assertTrue(ok)
        self.assertEqual(len(records), 4)
        self.assertTrue(all(record["status"] == "ok" for record in records))

    def test_steer_zero_verification_warns_when_off_center(self) -> None:
        hardware = self._hardware()
        motors = MockMotorClient()
        motors.positions[5] = math.radians(18.0)  # 轮端约 6 度
        motors.positions[6] = 0.0
        motors.positions[7] = 0.0
        motors.positions[8] = 0.0

        ok, records = verify_steer_zero(hardware, motors, tolerance_deg=5.0)

        self.assertFalse(ok)
        self.assertEqual(records[0]["status"], "warn")


if __name__ == "__main__":
    unittest.main()
