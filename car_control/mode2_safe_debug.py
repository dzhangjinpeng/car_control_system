from __future__ import annotations

from .config import ControlConfig, HardwareConfig
from .drive_smoothing import DriveSpeedRamping
from .kinematics import front_ackermann_plan
from .mapping import apply_drive_direction, motor_axis_target_deg, throttle_from_axis, turn_speed_scale
from .motor_client import MotorClient
from .state import ControlState
from .types import DriverInput


class Mode2SafeDebug:
    """低速调试模式：速度更低，转向更保守，适合先验车。"""

    def __init__(self, hardware: HardwareConfig, control: ControlConfig) -> None:
        self.hardware = hardware
        self.control = control
        self.drive_ramping = DriveSpeedRamping()

    def reset(self) -> None:
        # 切模式时重置速度斜坡缓存。
        self.drive_ramping.reset()

    def update(self, motors: MotorClient, state: ControlState, driver_input: DriverInput) -> None:
        # 这个模式不依赖额外状态，但保留签名方便和其他模式统一。
        # 只使用左摇杆 Y 轴做前后移动，并整体压低速度。
        linear_velocity = 0.0
        if abs(driver_input.left_y) >= self.control.deadzone:
            linear_velocity = throttle_from_axis(driver_input.left_y, self.control.max_linear_speed)
        linear_velocity = apply_drive_direction(linear_velocity, state.drive_direction_mode)
        linear_velocity *= self.control.mode2.speed_scale

        # 低速模式仍然允许转向，但给更小的最大角和更保守的速度曲线。
        steering_input = 0.0
        if abs(driver_input.left_x) >= self.control.deadzone:
            steering_input = driver_input.left_x

        if abs(steering_input) >= self.control.deadzone:
            linear_velocity *= turn_speed_scale(
                steering_input,
                self.control.mode2.turn_speed_min_scale,
                self.control.mode2.turn_speed_curve_power,
            )

        plan = front_ackermann_plan(
            linear_velocity=linear_velocity,
            steering_input=steering_input,
            wheelbase=self.hardware.wheelbase,
            track_width=self.hardware.track_width,
            max_inner_steering_degrees=self.control.mode2.max_inner_steering_degrees,
            enable_speed_compensation=self.control.mode2.enable_speed_compensation,
        )

        wheel_linear_speeds = self.drive_ramping.apply(
            plan.wheel_linear_speeds,
            self.control.drive_speed_ramp_mps_per_s * self.control.loop_period_s,
        )

        for role, motor_id in self.hardware.drive_motor_roles.items():
            speed = wheel_linear_speeds[role] / self.hardware.wheel_radius
            if motor_id in self.hardware.inverted_drive_motor_ids:
                speed = -speed
            motors.control_vel(motor_id, speed)

        for role, motor_id in self.hardware.steer_motor_roles.items():
            output_deg = plan.steering_output_degrees[role]
            motor_rad = motor_axis_target_deg(output_deg, self.hardware.gear_ratio)
            motors.control_pos_vel(motor_id, motor_rad, self.control.motor_speed_limit)
