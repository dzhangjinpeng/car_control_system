from __future__ import annotations

from dataclasses import dataclass

from .config import ControlConfig
from .types import DriverInput


def _clamp_axis(value: float) -> float:
    # 手柄轴值统一限制在 -1 到 1，避免异常输入放大到电机命令里。
    return max(-1.0, min(1.0, value))


def _shape_axis(value: float, power: float) -> float:
    # 曲线指数让小幅推动更细腻，同时保留满推时的最大输出。
    value = _clamp_axis(value)
    if value == 0.0:
        return 0.0
    sign = 1.0 if value > 0.0 else -1.0
    return sign * (abs(value) ** max(1.0, power))


def _smooth_axis(previous: float, target: float, alpha: float) -> float:
    # 一阶低通滤波，alpha 越大越接近原始输入，越小越平顺。
    alpha = max(0.0, min(1.0, alpha))
    return previous + (target - previous) * alpha


@dataclass
class InputSmoother:
    # 保存上一帧轴值，避免摇杆输入直接跳变成电机目标。
    control: ControlConfig
    left_x: float = 0.0
    left_y: float = 0.0
    right_x: float = 0.0
    right_y: float = 0.0
    initialized: bool = False

    def reset(self, driver_input: DriverInput | None = None) -> None:
        # 切模式时用当前输入作为新起点，避免上一模式的残留手感带到下一模式。
        if driver_input is None:
            self.left_x = self.left_y = self.right_x = self.right_y = 0.0
        else:
            self.left_x = _shape_axis(driver_input.left_x, self.control.steering_curve_power)
            self.left_y = _shape_axis(driver_input.left_y, self.control.throttle_curve_power)
            self.right_x = _shape_axis(driver_input.right_x, self.control.steering_curve_power)
            self.right_y = _shape_axis(driver_input.right_y, self.control.throttle_curve_power)
        self.initialized = True

    def apply(self, driver_input: DriverInput) -> DriverInput:
        # 按键保持原始值，只平滑摇杆轴值。
        if not self.initialized:
            self.reset()

        target_left_x = _shape_axis(driver_input.left_x, self.control.steering_curve_power)
        target_left_y = _shape_axis(driver_input.left_y, self.control.throttle_curve_power)
        target_right_x = _shape_axis(driver_input.right_x, self.control.steering_curve_power)
        target_right_y = _shape_axis(driver_input.right_y, self.control.throttle_curve_power)

        self.left_x = _smooth_axis(self.left_x, target_left_x, self.control.steering_smoothing_alpha)
        self.right_x = _smooth_axis(self.right_x, target_right_x, self.control.steering_smoothing_alpha)
        self.left_y = _smooth_axis(self.left_y, target_left_y, self.control.throttle_smoothing_alpha)
        self.right_y = _smooth_axis(self.right_y, target_right_y, self.control.throttle_smoothing_alpha)

        return DriverInput(
            left_x=self.left_x,
            left_y=self.left_y,
            right_x=self.right_x,
            right_y=self.right_y,
            mode_button=driver_input.mode_button,
            steering_lock_button=driver_input.steering_lock_button,
            drive_direction_button=driver_input.drive_direction_button,
            emergency_stop_button=driver_input.emergency_stop_button,
        )
