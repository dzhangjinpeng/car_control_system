from __future__ import annotations

from .config import HardwareConfig
from .motor_client import MotorClient


class SafetyStop:
    # 安全辅助函数保持简单、直接。
    def __init__(self, hardware: HardwareConfig) -> None:
        self.hardware = hardware

    def stop_drive_motors(self, motors: MotorClient) -> None:
        # 先把所有驱动轮清零，避免车继续滑行。
        for motor_id in self.hardware.drive_motor_ids:
            motors.control_vel(motor_id, 0.0)

    def center_steering(self, motors: MotorClient, velocity: float) -> None:
        # 需要回中时，把所有转向电机拉到零位。
        for motor_id in self.hardware.steer_motor_ids:
            motors.control_pos_vel(motor_id, 0.0, velocity)

    def emergency_stop(self, motors: MotorClient, velocity: float) -> None:
        # 紧急停车不关闭桥接层，只做立刻停驱动和回中转向。
        self.stop_drive_motors(motors)
        self.center_steering(motors, velocity)

    def shutdown(self, motors: MotorClient) -> None:
        # 正常退出时先停驱动，再关闭桥接层。
        self.stop_drive_motors(motors)
        motors.disable_all()
