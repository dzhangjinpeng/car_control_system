from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Mode0ControlConfig:
    # mode0 原地旋转时的轮速上限。
    max_rotation_wheel_speed: float
    # 转向电机回中时使用的速度。
    rotation_steer_speed: float
    # 转向轮被视为到位之前允许的误差。
    position_tolerance_rad: float
    # 直行时多久刷新一次回中命令。
    keep_zero_interval: int
    # 原地旋转时每个轮子的转向角。
    fixed_rotation_output_degrees: Dict[int, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Mode1ControlConfig:
    # 转向模型名称，目前只使用前轮阿克曼模型。
    steering_model: str
    # 方向输入来源，可选 left_x、right_x 或 auto。
    steering_axis: str
    # 内侧前轮允许的最大转角。
    max_inner_steering_degrees: float
    # 是否根据转弯半径补偿四个轮子的速度。
    enable_speed_compensation: bool
    # 转向越大时的最小速度比例。
    turn_speed_min_scale: float
    # 转向降速曲线指数。
    turn_speed_curve_power: float


@dataclass(frozen=True)
class Mode2ControlConfig:
    # 安全调试模式的速度缩放系数。
    speed_scale: float
    # 安全调试模式允许的最大内侧前轮转角。
    max_inner_steering_degrees: float
    # 安全调试模式是否进行转弯半径补偿。
    enable_speed_compensation: bool
    # 转向越大时的最小速度比例。
    turn_speed_min_scale: float
    # 转向降速曲线指数。
    turn_speed_curve_power: float


@dataclass(frozen=True)
class GamepadConfig:
    # 是否按手柄名称自动选择常见映射。
    auto_detect: bool
    # 左摇杆 X 轴的原始编号。
    left_x_axis: int
    # 左摇杆 Y 轴的原始编号。
    left_y_axis: int
    # 右摇杆 X 轴的原始编号。
    right_x_axis: int
    # 右摇杆 Y 轴的原始编号。
    right_y_axis: int
    # 切换控制模式的按键编号。
    mode_button: int
    # mode1 中切换转向锁的按键编号。
    steering_lock_button: int
    # 切换前进/倒车锁的按键编号。
    drive_direction_button: int
    # 紧急停车按键编号。
    emergency_stop_button: int
    # 轴值达到多少才算有效输入。
    deadzone: float


@dataclass(frozen=True)
class NetworkConfig:
    # 板子端 UDP 绑定地址。
    bind_host: str
    # 板子端 UDP 监听端口。
    port: int
    # 远程输入超时时间，单位秒。
    timeout_s: float
    # 接收 socket 的轮询超时，单位秒。
    poll_timeout_s: float


@dataclass(frozen=True)
class HardwareConfig:
    # USB-CANFD 设备序列号。
    serial_number: str
    # CAN 标称波特率。
    nom_baud: int
    # CAN-FD 数据波特率。
    dat_baud: int
    # C++ 桥接层共享库路径。
    bridge_library: str
    # 原始电机 CAN ID 列表。
    motor_ids: List[int]
    # 驱动电机 ID 列表。
    drive_motor_ids: List[int]
    # 转向电机 ID 列表。
    steer_motor_ids: List[int]
    # 需要反向的驱动电机 ID。
    inverted_drive_motor_ids: List[int]
    # 电机轴到轮端输出的减速比。
    gear_ratio: float
    # 轮子半径，单位米。
    wheel_radius: float
    # 轴距，单位米。
    wheelbase: float
    # 轮距，单位米。
    track_width: float
    # 驱动轮角色到电机 ID 的映射。
    drive_motor_roles: Dict[str, int]
    # 转向轮角色到电机 ID 的映射。
    steer_motor_roles: Dict[str, int]


@dataclass(frozen=True)
class ControlConfig:
    # 最大线速度。
    max_linear_speed: float
    # 安全回中时的转向电机速度。
    motor_speed_limit: float
    # 摇杆死区。
    deadzone: float
    # 油门平滑系数，越大响应越快。
    throttle_smoothing_alpha: float
    # 转向平滑系数，越大响应越快。
    steering_smoothing_alpha: float
    # 油门曲线指数，大于 1 时小幅推动更细腻。
    throttle_curve_power: float
    # 转向曲线指数，大于 1 时小角度更细腻。
    steering_curve_power: float
    # 驱动轮速度斜坡，单位 m/s^2。
    drive_speed_ramp_mps_per_s: float
    # 调试回显打印间隔，单位秒。
    telemetry_interval_s: float
    # 主循环周期，单位秒。
    loop_period_s: float
    # mode0 专用配置。
    mode0: Mode0ControlConfig
    # mode1 专用配置。
    mode1: Mode1ControlConfig
    # mode2 专用配置。
    mode2: Mode2ControlConfig


def _resolve_project_path(path: str | Path) -> Path:
    # 相对路径优先按当前工作目录找，找不到时再按项目根目录找。
    resolved = Path(path)
    if resolved.is_absolute() or resolved.exists():
        return resolved
    return PROJECT_ROOT / resolved


def _load_json(path: str | Path) -> dict:
    # 同时兼容普通 UTF-8 和带 BOM 的 UTF-8。
    return json.loads(_resolve_project_path(path).read_text(encoding="utf-8-sig"))


def load_hardware_config(path: str | Path = "configs/hardware.json") -> HardwareConfig:
    # 直接加载硬件配置。
    data = _load_json(path)
    bridge_library = Path(data["bridge_library"])
    if not bridge_library.is_absolute():
        data["bridge_library"] = str(PROJECT_ROOT / bridge_library)
    return HardwareConfig(**data)


def _apply_control_profile(control: ControlConfig, profile: dict) -> ControlConfig:
    # 把挡位配置叠加到基础控制参数上，方便在不改代码的情况下切换手感。
    top_level_keys = {
        "max_linear_speed",
        "motor_speed_limit",
        "deadzone",
        "throttle_smoothing_alpha",
        "steering_smoothing_alpha",
        "throttle_curve_power",
        "steering_curve_power",
        "drive_speed_ramp_mps_per_s",
        "telemetry_interval_s",
        "loop_period_s",
    }
    updates: dict[str, object] = {}
    for key in top_level_keys:
        if key in profile:
            updates[key] = profile[key]

    if "mode0" in profile:
        control = replace(control, mode0=replace(control.mode0, **profile["mode0"]))
    if "mode1" in profile:
        control = replace(control, mode1=replace(control.mode1, **profile["mode1"]))
    if "mode2" in profile:
        control = replace(control, mode2=replace(control.mode2, **profile["mode2"]))

    if updates:
        control = replace(control, **updates)
    return control


def load_control_config(
    path: str | Path = "configs/control.json",
    profile_name: str | None = None,
    profiles_path: str | Path = "configs/control_profiles.json",
) -> ControlConfig:
    # 把 JSON 里的嵌套字典转换成 dataclass。
    data = _load_json(path)

    mode0 = data.get("mode0", {})
    mode0["fixed_rotation_output_degrees"] = {
        int(k): float(v) for k, v in mode0.get("fixed_rotation_output_degrees", {}).items()
    }

    data["mode0"] = Mode0ControlConfig(**mode0)
    data["mode1"] = Mode1ControlConfig(**data.get("mode1", {}))
    data["mode2"] = Mode2ControlConfig(**data.get("mode2", {}))
    control = ControlConfig(**data)

    if profile_name:
        profiles = _load_json(profiles_path)
        if profile_name not in profiles:
            raise ValueError(f"unknown control profile: {profile_name}")
        control = _apply_control_profile(control, profiles[profile_name])

    return control


def load_gamepad_config(path: str | Path = "configs/input.json") -> GamepadConfig:
    # 加载手柄按键和摇杆映射。
    data = _load_json(path)
    data.setdefault("auto_detect", True)
    return GamepadConfig(**data)


def load_network_config(path: str | Path = "configs/network.json") -> NetworkConfig:
    # 加载远程控制的 UDP 配置。
    data = _load_json(path)
    return NetworkConfig(**data)


def validate_hardware_config(hardware: HardwareConfig) -> list[str]:
    # 只检查配置本身是否自洽，不依赖现场硬件。
    issues: list[str] = []
    all_ids = set(hardware.motor_ids)
    if len(all_ids) != len(hardware.motor_ids):
        issues.append("motor_ids 有重复")
    if not set(hardware.drive_motor_ids).issubset(all_ids):
        issues.append("drive_motor_ids 不是 motor_ids 的子集")
    if not set(hardware.steer_motor_ids).issubset(all_ids):
        issues.append("steer_motor_ids 不是 motor_ids 的子集")
    if set(hardware.drive_motor_ids) & set(hardware.steer_motor_ids):
        issues.append("drive_motor_ids 和 steer_motor_ids 有重叠")
    if not set(hardware.inverted_drive_motor_ids).issubset(set(hardware.drive_motor_ids)):
        issues.append("inverted_drive_motor_ids 不是 drive_motor_ids 的子集")
    if hardware.gear_ratio <= 0:
        issues.append("gear_ratio 必须大于 0")
    if hardware.wheel_radius <= 0:
        issues.append("wheel_radius 必须大于 0")
    if hardware.wheelbase <= 0:
        issues.append("wheelbase 必须大于 0")
    if hardware.track_width <= 0:
        issues.append("track_width 必须大于 0")
    if len(hardware.drive_motor_roles) != 4:
        issues.append("drive_motor_roles 数量不是 4")
    if len(hardware.steer_motor_roles) != 4:
        issues.append("steer_motor_roles 数量不是 4")
    role_ids = set(hardware.drive_motor_roles.values()) | set(hardware.steer_motor_roles.values())
    if not role_ids.issubset(all_ids):
        issues.append("角色映射里有未知电机 ID")
    return issues


def validate_control_config(control: ControlConfig) -> list[str]:
    # 控制参数只做基础范围检查，避免极端值把控制逻辑拖飞。
    issues: list[str] = []
    if control.max_linear_speed <= 0:
        issues.append("max_linear_speed 必须大于 0")
    if control.motor_speed_limit <= 0:
        issues.append("motor_speed_limit 必须大于 0")
    if not 0.0 <= control.deadzone <= 1.0:
        issues.append("deadzone 必须在 0 到 1 之间")
    if control.loop_period_s <= 0:
        issues.append("loop_period_s 必须大于 0")
    if control.telemetry_interval_s <= 0:
        issues.append("telemetry_interval_s 必须大于 0")
    if control.drive_speed_ramp_mps_per_s <= 0:
        issues.append("drive_speed_ramp_mps_per_s 必须大于 0")
    if control.mode1.max_inner_steering_degrees <= 0:
        issues.append("mode1.max_inner_steering_degrees 必须大于 0")
    if control.mode2.max_inner_steering_degrees <= 0:
        issues.append("mode2.max_inner_steering_degrees 必须大于 0")
    return issues
