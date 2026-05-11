from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.drive_smoothing import DriveSpeedRamping


class DriveSpeedRampingTest(unittest.TestCase):
    def test_apply_limits_speed_step(self) -> None:
        ramping = DriveSpeedRamping()
        first = ramping.apply({"front_left": 1.0}, 0.2)
        second = ramping.apply({"front_left": 1.0}, 0.2)

        self.assertAlmostEqual(first["front_left"], 0.2)
        self.assertAlmostEqual(second["front_left"], 0.4)

    def test_reset_clears_previous_state(self) -> None:
        ramping = DriveSpeedRamping()
        ramping.apply({"front_left": 1.0}, 0.2)
        ramping.reset()
        result = ramping.apply({"front_left": 1.0}, 0.2)

        self.assertAlmostEqual(result["front_left"], 0.2)


if __name__ == "__main__":
    unittest.main()
