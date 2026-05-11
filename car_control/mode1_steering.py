from __future__ import annotations

from .config import ControlConfig, HardwareConfig
from .drive_smoothing import DriveSpeedRamping
from .kinematics import front_ackermann_plan
from .mapping import apply_drive_direction, motor_axis_target_deg, throttle_from_axis, turn_speed_scale
from .motor_client import MotorClient
from .state import ControlState
from .types import DriverInput


class Mode1Steering:
    """遥控车模式：前轮转向，后轮保持居中。"""

    def __init__(self, hardware: HardwareConfig, control: ControlConfig) -> None:
        self.hardware = hardware
        self.control = control
        self.drive_ramping = DriveSpeedRamping()

    def reset(self) -> None:
        # 切模式时重置斜坡缓存，避免旧速度残留到新模式。
        self.drive_ramping.reset()

    def update(self, motors: MotorClient, state: ControlState, driver_input: DriverInput) -> None:
        # 前后速度只看左摇杆 Y 轴。
        linear_velocity = 0.0
        if abs(driver_input.left_y) >= self.control.deadzone:
            linear_velocity = throttle_from_axis(driver_input.left_y, self.control.max_linear_speed)
        linear_velocity = apply_drive_direction(linear_velocity, state.drive_direction_mode)

        # 转向锁关闭时才允许转向。
        steering_input = 0.0
        if not state.steering_locked:
            steering_input = self._steering_axis(driver_input)

        # 转向越大，自动把最高速度压低一些。
        if abs(steering_input) >= self.control.deadzone:
            linear_velocity *= turn_speed_scale(
                steering_input,
                self.control.mode1.turn_speed_min_scale,
                self.control.mode1.turn_speed_curve_power,
            )

        plan = front_ackermann_plan(
            linear_velocity=linear_velocity,
            steering_input=steering_input,
            wheelbase=self.hardware.wheelbase,
            track_width=self.hardware.track_width,
            max_inner_steering_degrees=self.control.mode1.max_inner_steering_degrees,
            enable_speed_compensation=self.control.mode1.enable_speed_compensation,
        )

        wheel_linear_speeds = self.drive_ramping.apply(
            plan.wheel_linear_speeds,
            self.control.drive_speed_ramp_mps_per_s * self.control.loop_period_s,
        )

        self._drive_by_role(motors, wheel_linear_speeds)
        self._steer_by_role(motors, plan.steering_output_degrees)

    def _drive_by_role(self, motors: MotorClient, wheel_linear_speeds: dict[str, float]) -> None:
        # 按角色把线速度换成电机速度后下发。
        for role, motor_id in self.hardware.drive_motor_roles.items():
            speed = wheel_linear_speeds[role] / self.hardware.wheel_radius
            if motor_id in self.hardware.inverted_drive_motor_ids:
                speed = -speed
            motors.control_vel(motor_id, speed)

    def _steer_by_role(self, motors: MotorClient, steering_output_degrees: dict[str, float]) -> None:
        # 前轮按阿克曼角度转向，后轮保持 0 度。
        for role, motor_id in self.hardware.steer_motor_roles.items():
            output_deg = steering_output_degrees[role]
            motor_rad = motor_axis_target_deg(output_deg, self.hardware.gear_ratio)
            motors.control_pos_vel(motor_id, motor_rad, self.control.mode0.rotation_steer_speed)

    def _steering_axis(self, driver_input: DriverInput) -> float:
        # 支持从左摇杆、右摇杆或自动模式中选取转向输入。
        source = self.control.mode1.steering_axis
        if source == "left_x":
            raw = driver_input.left_x
        elif source == "right_x":
            raw = driver_input.right_x
        elif source == "auto":
            raw = driver_input.right_x if abs(driver_input.right_x) >= self.control.deadzone else driver_input.left_x
        else:
            raise ValueError(f"unsupported mode1 steering_axis: {source}")
        return raw if abs(raw) >= self.control.deadzone else 0.0
