from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.config import load_control_config, load_hardware_config
from car_control.controller import CarController
from car_control.motor_client import MockMotorClient
from car_control.types import DriverInput


class CarControllerTest(unittest.TestCase):
    def test_mode1_outputs_drive_and_steering_commands(self) -> None:
        hardware = load_hardware_config()
        control = load_control_config()
        motors = MockMotorClient()
        controller = CarController(hardware, control, motors)

        controller.start()
        try:
            controller.update(DriverInput(mode_button=True))
            controller.update(DriverInput(mode_button=False, steering_lock_button=True))
            controller.update(DriverInput(left_y=-1.0, left_x=1.0))
        finally:
            controller.stop()

        self.assertEqual(controller.state.mode, 1)
        self.assertFalse(controller.state.steering_locked)
        self.assertTrue(any(command.startswith("vel:") for command in motors.commands))
        self.assertTrue(any(command.startswith("pos_vel:") for command in motors.commands))

    def test_emergency_stop_emits_zero_commands(self) -> None:
        hardware = load_hardware_config()
        control = load_control_config()
        motors = MockMotorClient()
        controller = CarController(hardware, control, motors)

        controller.start()
        try:
            before = len(motors.commands)
            controller.update(DriverInput(emergency_stop_button=True))
            recent = motors.commands[before:]
        finally:
            controller.stop()

        self.assertEqual(controller.state.mode, 0)
        self.assertTrue(any(command.startswith("vel:") and command.endswith(":0.000000") for command in recent))
        self.assertTrue(any(command.startswith("pos_vel:") and command.endswith(":2.500000") for command in recent))

    def test_drive_direction_button_cycles_direction_lock(self) -> None:
        hardware = load_hardware_config()
        control = load_control_config()
        motors = MockMotorClient()
        controller = CarController(hardware, control, motors)

        controller.start()
        try:
            controller.update(DriverInput(drive_direction_button=True))
            controller.update(DriverInput(drive_direction_button=False))
            controller.update(DriverInput(drive_direction_button=True))
        finally:
            controller.stop()

        self.assertEqual(controller.state.drive_direction_mode, 2)


if __name__ == "__main__":
    unittest.main()
