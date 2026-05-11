from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.kinematics import front_ackermann_plan


class FrontAckermannPlanTest(unittest.TestCase):
    def test_right_turn_uses_larger_inner_front_angle(self) -> None:
        plan = front_ackermann_plan(
            linear_velocity=0.5,
            steering_input=1.0,
            wheelbase=0.5,
            track_width=0.4,
            max_inner_steering_degrees=35.0,
            enable_speed_compensation=True,
        )

        self.assertGreater(plan.steering_output_degrees["front_right"], 34.9)
        self.assertGreater(plan.steering_output_degrees["front_right"], plan.steering_output_degrees["front_left"])
        self.assertEqual(plan.steering_output_degrees["rear_left"], 0.0)
        self.assertEqual(plan.steering_output_degrees["rear_right"], 0.0)
        self.assertGreater(plan.wheel_linear_speeds["front_left"], plan.wheel_linear_speeds["front_right"])

    def test_left_turn_uses_larger_inner_front_angle(self) -> None:
        plan = front_ackermann_plan(
            linear_velocity=0.5,
            steering_input=-1.0,
            wheelbase=0.5,
            track_width=0.4,
            max_inner_steering_degrees=35.0,
            enable_speed_compensation=True,
        )

        self.assertLess(plan.steering_output_degrees["front_left"], -34.9)
        self.assertLess(plan.steering_output_degrees["front_left"], plan.steering_output_degrees["front_right"])
        self.assertEqual(plan.steering_output_degrees["rear_left"], 0.0)
        self.assertEqual(plan.steering_output_degrees["rear_right"], 0.0)
        self.assertGreater(plan.wheel_linear_speeds["front_right"], plan.wheel_linear_speeds["front_left"])


if __name__ == "__main__":
    unittest.main()
