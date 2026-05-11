from __future__ import annotations

import time
from typing import Callable

from .config import ControlConfig, HardwareConfig
from .input_filter import InputSmoother
from .mode0_rotation import Mode0Rotation
from .mode1_steering import Mode1Steering
from .mode2_safe_debug import Mode2SafeDebug
from .motor_client import MotorClient
from .safety import SafetyStop
from .state import ControlState
from .types import DriverInput


InputProvider = Callable[[], DriverInput]
LoopObserver = Callable[[int, DriverInput, ControlState, MotorClient], None]


class CarController:
    # 统一协调输入、模式逻辑、安全停车和电机客户端。
    def __init__(self, hardware: HardwareConfig, control: ControlConfig, motors: MotorClient) -> None:
        self.hardware = hardware
        self.control = control
        self.motors = motors
        self.state = ControlState()
        self.mode0 = Mode0Rotation(hardware, control)
        self.mode1 = Mode1Steering(hardware, control)
        self.mode2 = Mode2SafeDebug(hardware, control)
        self.safety = SafetyStop(hardware)
        self.input_smoother = InputSmoother(control)

    def start(self) -> None:
        # 启动时先打开桥接层、使能电机，再把转向回中。
        self.motors.open()
        self.motors.enable_all()
        self.mode0.reset()
        self.mode1.reset()
        self.mode2.reset()
        self.input_smoother.reset()
        self.safety.center_steering(self.motors, self.control.motor_speed_limit)

    def stop(self) -> None:
        # 退出前先停驱动轮，再关闭桥接层。
        try:
            self.safety.shutdown(self.motors)
        finally:
            self.motors.close()

    def update(self, driver_input: DriverInput) -> DriverInput:
        # 紧急停车优先级最高，直接停驱动、回中并跳过本轮控制输出。
        if driver_input.emergency_stop_button:
            self.safety.emergency_stop(self.motors, self.control.motor_speed_limit)
            self.input_smoother.reset(driver_input)
            self.mode0.reset()
            self.mode1.reset()
            self.mode2.reset()
            self.state.rotation_ready = False
            self.state.advance_loop()
            return driver_input

        # 按键使用原始输入，避免平滑逻辑影响模式切换。
        toggled = self.state.update_mode_button(driver_input.mode_button)
        self.state.update_steering_lock_button(driver_input.steering_lock_button)
        direction_toggled = self.state.update_drive_direction_button(driver_input.drive_direction_button)

        # 切模式时先停稳并回中，避免上一个模式的目标残留。
        if toggled:
            self.safety.stop_drive_motors(self.motors)
            self.safety.center_steering(self.motors, self.control.motor_speed_limit)
            self.input_smoother.reset(driver_input)
            self.mode0.reset()
            self.mode1.reset()
            self.mode2.reset()
        elif direction_toggled:
            self.mode0.reset()
            self.mode1.reset()
            self.mode2.reset()

        # 摇杆轴值经过曲线和平滑后再进入具体模式。
        smoothed_input = self.input_smoother.apply(driver_input)

        if self.state.mode == 0:
            self.mode0.update(self.motors, self.state, smoothed_input)
        elif self.state.mode == 1:
            self.mode1.update(self.motors, self.state, smoothed_input)
        else:
            self.mode2.update(self.motors, self.state, smoothed_input)

        self.state.advance_loop()
        return smoothed_input

    def run(
        self,
        input_provider: InputProvider,
        max_loops: int | None = None,
        observer: LoopObserver | None = None,
    ) -> None:
        # 主循环只负责调度，具体控制行为放在各模式模块里。
        self.start()
        try:
            loops = 0
            while max_loops is None or loops < max_loops:
                start = time.monotonic()
                raw_input = input_provider()
                smoothed_input = self.update(raw_input)
                if observer is not None:
                    observer(loops, smoothed_input, self.state, self.motors)
                loops += 1
                sleep_s = self.control.loop_period_s - (time.monotonic() - start)
                if sleep_s > 0:
                    time.sleep(sleep_s)
        finally:
            self.stop()
