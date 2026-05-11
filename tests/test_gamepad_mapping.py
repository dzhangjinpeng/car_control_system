from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.config import GamepadConfig
from car_control.gamepad_input import detect_pygame_gamepad_config


class GamepadMappingTest(unittest.TestCase):
    def _base_config(self, auto_detect: bool = True) -> GamepadConfig:
        return GamepadConfig(
            auto_detect=auto_detect,
            left_x_axis=0,
            left_y_axis=1,
            right_x_axis=2,
            right_y_axis=3,
            mode_button=1,
            steering_lock_button=4,
            drive_direction_button=5,
            emergency_stop_button=6,
            deadzone=0.15,
        )

    def test_xbox_name_uses_xinput_style_mapping(self) -> None:
        config = detect_pygame_gamepad_config(self._base_config(), "Xbox Wireless Controller", 6, 12)

        self.assertEqual(config.right_x_axis, 2)
        self.assertEqual(config.right_y_axis, 3)
        self.assertEqual(config.emergency_stop_button, 6)

    def test_playstation_name_uses_common_sdl_mapping(self) -> None:
        config = detect_pygame_gamepad_config(self._base_config(), "DualSense Wireless Controller", 6, 14)

        self.assertEqual(config.right_x_axis, 3)
        self.assertEqual(config.right_y_axis, 4)
        self.assertEqual(config.emergency_stop_button, 8)

    def test_manual_config_is_not_changed_when_auto_detect_disabled(self) -> None:
        base = self._base_config(auto_detect=False)
        config = detect_pygame_gamepad_config(base, "DualSense Wireless Controller", 6, 14)

        self.assertEqual(config, base)


if __name__ == "__main__":
    unittest.main()
