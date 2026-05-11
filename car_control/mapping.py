from __future__ import annotations

import math

from .math_utils import clamp, deg_to_rad, rad_to_deg
from .types import StickState
from .state import DRIVE_DIRECTION_AUTO, DRIVE_DIRECTION_FORWARD_ONLY, DRIVE_DIRECTION_REVERSE_ONLY


def read_stick(x: float, y: float, deadzone: float) -> StickState:
    # 先过滤掉很小的摇杆噪声，再计算角度和幅值。
    if abs(x) < deadzone:
        x = 0.0
    if abs(y) < deadzone:
        y = 0.0

    magnitude = clamp((x * x + y * y) ** 0.5, 0.0, 1.0)
    if magnitude < deadzone:
        return StickState(angle_deg=0.0, magnitude=0.0)

    return StickState(angle_deg=rad_to_deg(math.atan2(-y, x)), magnitude=magnitude)


def map_stick_to_steer_angle(stick_deg: float) -> float:
    # 保留旧版代码里的角度映射方式。
    if stick_deg >= 0.0:
        value = 90.0 - stick_deg
        if stick_deg > 179.0:
            value = -90.0
        return value
    if stick_deg >= -90.0:
        return -90.0 - stick_deg
    return -(stick_deg + 90.0)


def signed_linear_velocity(angle_deg: float, magnitude: float, max_linear_speed: float) -> float:
    # 摇杆上半区表示前进，下半区表示后退。
    velocity = max_linear_speed * magnitude
    return velocity if angle_deg >= 0.0 else -velocity


def throttle_from_axis(axis_y: float, max_linear_speed: float) -> float:
    # 左摇杆 Y 轴向上时给正速度，向下时给负速度。
    return -max(-1.0, min(1.0, axis_y)) * max_linear_speed


def apply_drive_direction(linear_velocity: float, drive_direction_mode: int) -> float:
    # 方向锁只约束最终速度的正负，不改变转向模型和模式逻辑。
    if drive_direction_mode == DRIVE_DIRECTION_FORWARD_ONLY:
        return abs(linear_velocity)
    if drive_direction_mode == DRIVE_DIRECTION_REVERSE_ONLY:
        return -abs(linear_velocity)
    if drive_direction_mode == DRIVE_DIRECTION_AUTO:
        return linear_velocity
    return linear_velocity


def steering_from_axis(axis_x: float, max_steering_output_degrees: float) -> float:
    # 右/左摇杆 X 轴直接映射成转角目标。
    return max(-1.0, min(1.0, axis_x)) * max_steering_output_degrees


def turn_speed_scale(steering_input: float, min_speed_scale: float, curve_power: float) -> float:
    # 转向越大，车速越低；直行时保持 1.0，满转时降到最小比例。
    turn = clamp(abs(steering_input), 0.0, 1.0)
    min_speed_scale = clamp(min_speed_scale, 0.0, 1.0)
    curve_power = max(1.0, curve_power)
    return min_speed_scale + (1.0 - min_speed_scale) * (1.0 - turn**curve_power)


def motor_axis_target_deg(output_deg: float, gear_ratio: float) -> float:
    # 把轮端角度换算成电机轴角度。
    return deg_to_rad(output_deg) * gear_ratio
