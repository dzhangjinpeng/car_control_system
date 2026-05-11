from __future__ import annotations

from dataclasses import dataclass


MODE_COUNT = 3
DRIVE_DIRECTION_AUTO = 0
DRIVE_DIRECTION_FORWARD_ONLY = 1
DRIVE_DIRECTION_REVERSE_ONLY = 2


@dataclass
class ControlState:
    # 0 = 兼容原地旋转模式，1 = 遥控车模式，2 = 低速调试模式。
    mode: int = 0
    # 用于按键上升沿检测，避免一次按下重复切换模式。
    last_mode_button: bool = False
    # mode1 的转向锁：True 表示只允许前后，不启用转向。
    steering_locked: bool = True
    # 用于转向锁按键上升沿检测。
    last_steering_lock_button: bool = False
    # 前进/倒车方向锁：0 自动，1 只准前进，2 只准倒车。
    drive_direction_mode: int = DRIVE_DIRECTION_AUTO
    # 用于方向锁按键上升沿检测。
    last_drive_direction_button: bool = False
    # mode0 原地旋转时，转向轮还没到位前不允许驱动轮旋转。
    rotation_ready: bool = False
    # 主循环计数器。
    loop_count: int = 0

    def update_mode_button(self, pressed: bool) -> bool:
        # 只在按键从未按下变成按下时切换一次模式。
        toggled = pressed and not self.last_mode_button
        if toggled:
            self.mode = (self.mode + 1) % MODE_COUNT
            self.rotation_ready = False
            if self.mode == 1:
                self.steering_locked = True
        self.last_mode_button = pressed
        return toggled

    def update_steering_lock_button(self, pressed: bool) -> bool:
        # 只在上升沿切换转向锁。
        toggled = pressed and not self.last_steering_lock_button
        if toggled:
            self.steering_locked = not self.steering_locked
        self.last_steering_lock_button = pressed
        return toggled

    def update_drive_direction_button(self, pressed: bool) -> bool:
        # 每按一次就循环一次方向锁：自动 -> 只前进 -> 只倒车 -> 自动。
        toggled = pressed and not self.last_drive_direction_button
        if toggled:
            self.drive_direction_mode = (self.drive_direction_mode + 1) % 3
        self.last_drive_direction_button = pressed
        return toggled

    def advance_loop(self) -> None:
        # 统一维护循环计数。
        self.loop_count += 1
