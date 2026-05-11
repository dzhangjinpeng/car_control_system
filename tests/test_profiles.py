from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.config import load_control_config


class ControlProfileTest(unittest.TestCase):
    def test_sport_profile_is_faster_than_conservative(self) -> None:
        conservative = load_control_config(profile_name="conservative")
        sport = load_control_config(profile_name="sport")

        self.assertGreater(sport.max_linear_speed, conservative.max_linear_speed)
        self.assertGreater(sport.drive_speed_ramp_mps_per_s, conservative.drive_speed_ramp_mps_per_s)
        self.assertLess(sport.mode1.turn_speed_min_scale, conservative.mode1.turn_speed_min_scale)


if __name__ == "__main__":
    unittest.main()
