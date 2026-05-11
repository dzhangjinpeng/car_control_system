from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import replace

from .config import GamepadConfig
from .types import DriverInput


# 备用后端启用时，`configs/input.json` 里使用的 XInput 按键顺序。
# 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=BACK, 7=START, 8=左摇杆按下, 9=右摇杆按下。
_XINPUT_BUTTON_MASKS = [
    0x1000,
    0x2000,
    0x4000,
    0x8000,
    0x0100,
    0x0200,
    0x0020,
    0x0010,
    0x0040,
    0x0080,
]


def detect_pygame_gamepad_config(
    base_config: GamepadConfig,
    device_name: str,
    axis_count: int,
    button_count: int,
) -> GamepadConfig:
    # 不开启自动识别时，完全使用 input.json 里的手动配置。
    if not base_config.auto_detect:
        return base_config

    normalized_name = device_name.lower()

    # Xbox / XInput 类手柄在 SDL 下通常就是这套编号。
    if "xbox" in normalized_name or "xinput" in normalized_name:
        return replace(
            base_config,
            left_x_axis=0,
            left_y_axis=1,
            right_x_axis=2,
            right_y_axis=3,
            mode_button=1,
            steering_lock_button=4,
            drive_direction_button=5,
            emergency_stop_button=6,
        )

    # PlayStation 手柄在 SDL/pygame 下常见右摇杆是 3/4，Share/Back 常见是 8。
    if (
        "playstation" in normalized_name
        or "dualshock" in normalized_name
        or "dualsense" in normalized_name
        or "wireless controller" in normalized_name
    ):
        return replace(
            base_config,
            left_x_axis=0,
            left_y_axis=1,
            right_x_axis=3 if axis_count > 3 else base_config.right_x_axis,
            right_y_axis=4 if axis_count > 4 else base_config.right_y_axis,
            mode_button=1 if button_count > 1 else base_config.mode_button,
            steering_lock_button=4 if button_count > 4 else base_config.steering_lock_button,
            drive_direction_button=5 if button_count > 5 else base_config.drive_direction_button,
            emergency_stop_button=8 if button_count > 8 else base_config.emergency_stop_button,
        )

    # 常见 SDL 手柄：轴数量够用时沿用 Xbox 风格，按键不乱猜。
    if axis_count >= 4:
        return replace(base_config, left_x_axis=0, left_y_axis=1, right_x_axis=2, right_y_axis=3)

    return base_config


def describe_gamepads() -> list[str]:
    # 打印本机能看到的手柄名称、轴数量、按键数量，用于现场核对映射。
    lines: list[str] = []
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame  # type: ignore
    except ModuleNotFoundError:
        lines.append("未安装 pygame，无法枚举 SDL/pygame 手柄。")
    else:
        pygame.init()
        pygame.joystick.init()
        try:
            count = pygame.joystick.get_count()
            if count <= 0:
                lines.append("pygame 没有检测到手柄。")
            for index in range(count):
                joystick = pygame.joystick.Joystick(index)
                joystick.init()
                lines.append(
                    f"pygame index={index} 名称={joystick.get_name()} "
                    f"轴={joystick.get_numaxes()} 按键={joystick.get_numbuttons()} "
                    f"帽键={joystick.get_numhats()}"
                )
                joystick.quit()
        finally:
            pygame.joystick.quit()
            pygame.quit()

    if sys.platform.startswith("win"):
        xinput_lines = _describe_xinput_gamepads()
        if xinput_lines:
            lines.extend(xinput_lines)

    return lines or ["没有检测到手柄。"]


def _describe_xinput_gamepads() -> list[str]:
    # Windows 上补充枚举 XInput 槽位，解决 Xbox 蓝牙手柄不出现在 pygame 列表里的情况。
    for dll_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            dll = getattr(ctypes.windll, dll_name)
            dll.XInputGetState.argtypes = [ctypes.c_uint, ctypes.POINTER(_XInputState)]
            dll.XInputGetState.restype = ctypes.c_uint
            break
        except Exception:
            dll = None
    if dll is None:
        return []

    lines = []
    for index in range(4):
        state = _XInputState()
        if dll.XInputGetState(index, ctypes.byref(state)) == 0:
            lines.append(f"XInput index={index} 名称=Xbox/XInput 兼容手柄")
    return lines


class _XInputGamepad(ctypes.Structure):
    # Windows API 里的原始 XInput 手柄数据结构。
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XInputState(ctypes.Structure):
    # XInput 返回一个包计数器和当前手柄状态。
    _fields_ = [
        ("dwPacketNumber", ctypes.c_ulong),
        ("Gamepad", _XInputGamepad),
    ]


def _normalize_xinput_axis(value: int, deadzone: float) -> float:
    # 把有符号 16 位摇杆值转换成和 pygame 一样的 -1..1 范围。
    scale = 32767.0 if value >= 0 else 32768.0
    normalized = max(-1.0, min(1.0, value / scale))
    if abs(normalized) < deadzone:
        return 0.0
    return normalized


def _xinput_button_pressed(buttons: int, button_index: int) -> bool:
    # 按固定的 XInput 顺序解释配置里的按键编号。
    if button_index < 0 or button_index >= len(_XINPUT_BUTTON_MASKS):
        return False
    return bool(buttons & _XINPUT_BUTTON_MASKS[button_index])


class _WindowsXInputBackend:
    """通过 Windows XInput API 读取 Xbox 兼容手柄。"""

    def __init__(self, config: GamepadConfig, device_index: int) -> None:
        self.config = config
        self.device_index = device_index
        self._dll = None

    def open(self) -> None:
        # XInput 只支持 4 个控制器槽位。
        if self.device_index < 0 or self.device_index > 3:
            raise RuntimeError(f"XInput gamepad index out of range: {self.device_index}")

        last_error: Exception | None = None
        for dll_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                dll = getattr(ctypes.windll, dll_name)
                dll.XInputGetState.argtypes = [ctypes.c_uint, ctypes.POINTER(_XInputState)]
                dll.XInputGetState.restype = ctypes.c_uint
                self._dll = dll
                break
            except Exception as exc:  # pragma: no cover - 依赖本机 Windows DLL。
                last_error = exc
        if self._dll is None:
            raise RuntimeError(f"XInput is not available: {last_error}")

        # 校验目标控制器槽位是否真的连着设备。
        self._read_state()

    def close(self) -> None:
        # XInput 不需要显式关闭设备。
        self._dll = None

    def poll(self) -> DriverInput:
        state = self._read_state()
        gamepad = state.Gamepad
        return DriverInput(
            left_x=_normalize_xinput_axis(gamepad.sThumbLX, self.config.deadzone),
            left_y=-_normalize_xinput_axis(gamepad.sThumbLY, self.config.deadzone),
            right_x=_normalize_xinput_axis(gamepad.sThumbRX, self.config.deadzone),
            right_y=-_normalize_xinput_axis(gamepad.sThumbRY, self.config.deadzone),
            mode_button=_xinput_button_pressed(gamepad.wButtons, self.config.mode_button),
            steering_lock_button=_xinput_button_pressed(gamepad.wButtons, self.config.steering_lock_button),
            drive_direction_button=_xinput_button_pressed(gamepad.wButtons, self.config.drive_direction_button),
            emergency_stop_button=_xinput_button_pressed(gamepad.wButtons, self.config.emergency_stop_button),
        )

    def _read_state(self) -> _XInputState:
        if self._dll is None:
            raise RuntimeError("XInput gamepad input is not open")

        state = _XInputState()
        result = self._dll.XInputGetState(self.device_index, ctypes.byref(state))
        if result != 0:
            raise RuntimeError(f"no XInput gamepad detected at index {self.device_index}")
        return state


class PygameGamepadInput:
    """读取真实手柄并转换成 DriverInput。"""

    def __init__(self, config: GamepadConfig, device_index: int = 0) -> None:
        self.config = config
        self.device_index = device_index
        self._pygame = None
        self._joystick = None
        self._fallback = None

    def open(self) -> None:
        # 优先用 pygame/SDL，因为它对更多手柄品牌都兼容。
        pygame_error = self._open_pygame_if_available()
        if pygame_error is None:
            return

        # 在 Windows 上，Xbox 兼容手柄有时不会被 pygame 列成 joystick，
        # 但 XInput 仍然能读到。
        if sys.platform.startswith("win"):
            self._fallback = _WindowsXInputBackend(self.config, self.device_index)
            try:
                self._fallback.open()
                return
            except RuntimeError as xinput_error:
                self._fallback = None
                raise RuntimeError(
                    f"no gamepad detected by pygame or XInput; pygame={pygame_error}; "
                    f"xinput={xinput_error}"
                ) from xinput_error

        raise RuntimeError(f"no gamepad detected by pygame; {pygame_error}")

    def close(self) -> None:
        # 让 pygame 正常退出，释放设备占用。
        if self._joystick is not None:
            self._joystick.quit()
        if self._pygame is not None:
            self._pygame.joystick.quit()
            self._pygame.quit()
        if self._fallback is not None:
            self._fallback.close()
        self._joystick = None
        self._pygame = None
        self._fallback = None

    def poll(self) -> DriverInput:
        if self._fallback is not None:
            return self._fallback.poll()
        if self._pygame is None or self._joystick is None:
            raise RuntimeError("gamepad input is not open")

        # 先泵一下事件队列，保证轴值是最新的。
        self._pygame.event.pump()
        return DriverInput(
            left_x=self._axis(self.config.left_x_axis),
            left_y=self._axis(self.config.left_y_axis),
            right_x=self._axis(self.config.right_x_axis),
            right_y=self._axis(self.config.right_y_axis),
            mode_button=bool(self._button(self.config.mode_button)),
            steering_lock_button=bool(self._button(self.config.steering_lock_button)),
            drive_direction_button=bool(self._button(self.config.drive_direction_button)),
            emergency_stop_button=bool(self._button(self.config.emergency_stop_button)),
        )

    def _open_pygame_if_available(self) -> str | None:
        # 把 pygame 的启动提示压掉，避免控制台太吵。
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        try:
            import pygame  # type: ignore
        except ModuleNotFoundError:
            return "pygame is not installed; run: python -m pip install pygame"

        pygame.init()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        if count <= 0:
            pygame.joystick.quit()
            pygame.quit()
            return "pygame joystick count is 0"
        if self.device_index < 0 or self.device_index >= count:
            pygame.joystick.quit()
            pygame.quit()
            return f"pygame gamepad index out of range: {self.device_index}, count={count}"

        joystick = pygame.joystick.Joystick(self.device_index)
        joystick.init()
        detected_config = detect_pygame_gamepad_config(
            self.config,
            joystick.get_name(),
            joystick.get_numaxes(),
            joystick.get_numbuttons(),
        )
        if detected_config != self.config:
            print(
                f"已自动匹配手柄映射：{joystick.get_name()} "
                f"轴=({detected_config.left_x_axis},{detected_config.left_y_axis},"
                f"{detected_config.right_x_axis},{detected_config.right_y_axis}) "
                f"按键=(模式{detected_config.mode_button},转向锁{detected_config.steering_lock_button},"
                f"方向锁{detected_config.drive_direction_button},急停{detected_config.emergency_stop_button})"
            )
        self.config = detected_config
        self._pygame = pygame
        self._joystick = joystick
        return None

    def _axis(self, index: int) -> float:
        if index < 0 or index >= self._joystick.get_numaxes():
            return 0.0
        return float(self._joystick.get_axis(index))

    def _button(self, index: int) -> int:
        if index < 0 or index >= self._joystick.get_numbuttons():
            return 0
        return int(self._joystick.get_button(index))
