from __future__ import annotations

from dataclasses import dataclass
import math


WHEEL_ROLES = ("front_left", "front_right", "rear_left", "rear_right")


@dataclass(frozen=True)
class WheelPlan:
    # 每个轮子角色对应的目标转向角。
    steering_output_degrees: dict[str, float]
    # 每个轮子角色对应的目标线速度。
    wheel_linear_speeds: dict[str, float]


def front_ackermann_plan(
    linear_velocity: float,
    steering_input: float,
    wheelbase: float,
    track_width: float,
    max_inner_steering_degrees: float,
    enable_speed_compensation: bool,
) -> WheelPlan:
    # 先把输入限制在合理范围内，避免求解器跑飞。
    steering_input = max(-1.0, min(1.0, steering_input))
    if abs(steering_input) < 1e-6:
        return WheelPlan(
            steering_output_degrees={role: 0.0 for role in WHEEL_ROLES},
            wheel_linear_speeds={role: linear_velocity for role in WHEEL_ROLES},
        )

    # 以内侧前轮作为参考转角。
    inner_deg = abs(steering_input) * max_inner_steering_degrees
    inner_rad = math.radians(inner_deg)
    if inner_rad <= 1e-6:
        return WheelPlan(
            steering_output_degrees={role: 0.0 for role in WHEEL_ROLES},
            wheel_linear_speeds={role: linear_velocity for role in WHEEL_ROLES},
        )

    turn_sign = 1.0 if steering_input > 0.0 else -1.0
    half_track = track_width / 2.0
    # 根据内侧前轮角度计算转弯中心半径。
    center_radius = wheelbase / math.tan(inner_rad) + half_track
    outer_deg = math.degrees(math.atan(wheelbase / (center_radius + half_track)))

    if turn_sign > 0.0:
        front_left = outer_deg
        front_right = inner_deg
    else:
        front_left = -inner_deg
        front_right = -outer_deg

    steering = {
        "front_left": front_left,
        "front_right": front_right,
        "rear_left": 0.0,
        "rear_right": 0.0,
    }

    speeds = {role: linear_velocity for role in WHEEL_ROLES}
    if enable_speed_compensation:
        # 外侧轮子走的弧长更长，所以速度也要按比例放大。
        inner_side_radius = center_radius - half_track
        outer_side_radius = center_radius + half_track
        front_inner_radius = math.hypot(inner_side_radius, wheelbase)
        front_outer_radius = math.hypot(outer_side_radius, wheelbase)

        if turn_sign > 0.0:
            radii = {
                "front_left": front_outer_radius,
                "front_right": front_inner_radius,
                "rear_left": outer_side_radius,
                "rear_right": inner_side_radius,
            }
        else:
            radii = {
                "front_left": front_inner_radius,
                "front_right": front_outer_radius,
                "rear_left": inner_side_radius,
                "rear_right": outer_side_radius,
            }
        speeds = {role: linear_velocity * (radius / center_radius) for role, radius in radii.items()}

    return WheelPlan(steering_output_degrees=steering, wheel_linear_speeds=speeds)
