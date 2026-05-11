from __future__ import annotations

from .config import ControlConfig, HardwareConfig
from .drive_smoothing import DriveSpeedRamping
from .mapping import apply_drive_direction, motor_axis_target_deg, read_stick, signed_linear_velocity
from .motor_client import MotorClient
from .state import ControlState
from .types import DriverInput


class Mode0Rotation:
    """旧兼容模式：左摇杆直行，右摇杆 X 轴原地旋转。"""

    def __init__(self, hardware: HardwareConfig, control: ControlConfig) -> None:
        self.hardware = hardware
        self.control = control
        self.drive_ramping = DriveSpeedRamping()

    def reset(self) -> None:
        # 切模式时清掉当前斜坡状态。
        self.drive_ramping.reset()

    def update(self, motors: MotorClient, state: ControlState, driver_input: DriverInput) -> None:
        # mode0 保留原始两条路径：直行，或者原地旋转。
        left = read_stick(driver_input.left_x, driver_input.left_y, self.control.deadzone)
        right_x = driver_input.right_x if abs(driver_input.right_x) >= self.control.deadzone else 0.0

        if right_x == 0.0:
            state.rotation_ready = False
            self._drive_straight(motors, left.angle_deg, left.magnitude, state.drive_direction_mode)
            self._periodic_zero_steering(motors, state.loop_count)
            return

        self._point_wheels_for_rotation(motors)
        if not state.rotation_ready:
            state.rotation_ready = self._rotation_angles_reached(motors)

        if state.rotation_ready:
            self._drive_rotation(motors, right_x)
        else:
            self._stop_drive_motors(motors)

    def _drive_straight(
        self,
        motors: MotorClient,
        left_angle_deg: float,
        left_magnitude: float,
        drive_direction_mode: int,
    ) -> None:
        # 左摇杆决定前后速度，再通过斜坡限制一下变化率。
        linear_velocity = signed_linear_velocity(left_angle_deg, left_magnitude, self.control.max_linear_speed)
        linear_velocity = apply_drive_direction(linear_velocity, drive_direction_mode)
        wheel_speed = linear_velocity / self.hardware.wheel_radius
        wheel_linear_speeds = {
            "rear_right": wheel_speed * self.hardware.wheel_radius,
            "rear_left": wheel_speed * self.hardware.wheel_radius,
            "front_left": wheel_speed * self.hardware.wheel_radius,
            "front_right": wheel_speed * self.hardware.wheel_radius,
        }
        wheel_linear_speeds = self.drive_ramping.apply(
            wheel_linear_speeds,
            self.control.drive_speed_ramp_mps_per_s * self.control.loop_period_s,
        )
        self._set_drive_speeds(motors, wheel_linear_speeds)

    def _periodic_zero_steering(self, motors: MotorClient, loop_count: int) -> None:
        # 直行时定期把转向拉回零位。
        if loop_count <= 0 or loop_count % self.control.mode0.keep_zero_interval != 0:
            return
        for motor_id in self.hardware.steer_motor_ids:
            motors.control_pos_vel(motor_id, 0.0, self.control.mode0.rotation_steer_speed)

    def _point_wheels_for_rotation(self, motors: MotorClient) -> None:
        # 原地旋转时，先把四个转向电机打到预设角度。
        for motor_id in self.hardware.steer_motor_ids:
            output_deg = self.control.mode0.fixed_rotation_output_degrees[motor_id]
            motor_rad = motor_axis_target_deg(output_deg, self.hardware.gear_ratio)
            motors.control_pos_vel(motor_id, motor_rad, self.control.mode0.rotation_steer_speed)

    def _rotation_angles_reached(self, motors: MotorClient) -> bool:
        # 四个转向电机都到位后，才允许驱动轮开始旋转。
        for motor_id in self.hardware.steer_motor_ids:
            output_deg = self.control.mode0.fixed_rotation_output_degrees[motor_id]
            target = motor_axis_target_deg(output_deg, self.hardware.gear_ratio)
            if abs(motors.get_position(motor_id) - target) > self.control.mode0.position_tolerance_rad:
                return False
        return True

    def _drive_rotation(self, motors: MotorClient, right_x: float) -> None:
        # 右摇杆 X 轴决定原地旋转速度和方向。
        speed = abs(right_x) * self.control.mode0.max_rotation_wheel_speed
        sign = 1.0 if right_x > 0.0 else -1.0
        wheel_linear_speeds = {
            "rear_right": speed * sign * self.hardware.wheel_radius,
            "rear_left": -speed * sign * self.hardware.wheel_radius,
            "front_left": -speed * sign * self.hardware.wheel_radius,
            "front_right": speed * sign * self.hardware.wheel_radius,
        }
        wheel_linear_speeds = self.drive_ramping.apply(
            wheel_linear_speeds,
            self.control.drive_speed_ramp_mps_per_s * self.control.loop_period_s,
        )
        self._set_drive_speeds(motors, wheel_linear_speeds)

    def _stop_drive_motors(self, motors: MotorClient) -> None:
        self._set_drive_speeds(motors, {role: 0.0 for role in self.hardware.drive_motor_roles})

    def _set_drive_speeds(self, motors: MotorClient, wheel_linear_speeds: dict[str, float]) -> None:
        # 按角色把轮端线速度换算成电机速度。
        for role, motor_id in self.hardware.drive_motor_roles.items():
            speed = wheel_linear_speeds[role] / self.hardware.wheel_radius
            if motor_id in self.hardware.inverted_drive_motor_ids:
                speed = -speed
            motors.control_vel(motor_id, speed)
