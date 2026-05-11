from __future__ import annotations

import argparse
import math
import time
from typing import Callable

from car_control.config import (
    ControlConfig,
    HardwareConfig,
    load_control_config,
    load_gamepad_config,
    load_hardware_config,
    load_network_config,
)
from car_control.controller import CarController
from car_control.gamepad_input import PygameGamepadInput
from car_control.keyboard_input import ScriptedInput, neutral_input
from car_control.motor_client import CxxMotorClient, MockMotorClient, MotorClient
from car_control.network_input import HybridInputSource, UdpRemoteInput
from car_control.state import (
    DRIVE_DIRECTION_AUTO,
    DRIVE_DIRECTION_FORWARD_ONLY,
    DRIVE_DIRECTION_REVERSE_ONLY,
    ControlState,
)
from car_control.types import DriverInput


MODE_NAMES = {
    0: "兼容原地旋转",
    1: "遥控车转向",
    2: "低速调试",
}

DIRECTION_NAMES = {
    DRIVE_DIRECTION_AUTO: "自动",
    DRIVE_DIRECTION_FORWARD_ONLY: "只前进",
    DRIVE_DIRECTION_REVERSE_ONLY: "只倒车",
}


def build_motor_client(args: argparse.Namespace, hardware: HardwareConfig) -> MotorClient:
    # mock 表示不连真实硬件，只把电机命令记录在内存里。
    if args.mock:
        return MockMotorClient()
    return CxxMotorClient(hardware.bridge_library, hardware.serial_number, hardware.nom_baud, hardware.dat_baud)


def build_demo_input_provider(args: argparse.Namespace) -> Callable[[], DriverInput]:
    # demo 和 neutral 用于本地快速检查，不依赖真实手柄。
    if args.input == "neutral":
        return neutral_input
    if args.input == "demo":
        frames = [
            DriverInput(left_y=-1.0),
            DriverInput(left_y=-1.0),
            DriverInput(right_x=1.0, mode_button=True),
            DriverInput(left_y=-1.0, left_x=0.6),
            DriverInput(left_y=-1.0, left_x=0.0, drive_direction_button=True),
            DriverInput(left_y=1.0, left_x=0.0),
            DriverInput(left_y=-1.0, left_x=0.0, emergency_stop_button=True),
        ]
        scripted = ScriptedInput(frames)
        return scripted.next
    raise ValueError(f"unsupported input mode: {args.input}")


def _drive_summary(hardware: HardwareConfig, motors: MotorClient) -> str:
    # 打印驱动轮电机目标速度，单位是电机接口使用的 rad/s。
    parts = []
    for role, motor_id in hardware.drive_motor_roles.items():
        parts.append(f"{role}#{motor_id}:{motors.get_velocity(motor_id):+.2f}")
    return " ".join(parts)


def _steer_summary(hardware: HardwareConfig, motors: MotorClient) -> str:
    # 转向电机保存的是电机轴弧度，这里换算回轮端角度，方便肉眼判断。
    parts = []
    for role, motor_id in hardware.steer_motor_roles.items():
        motor_rad = motors.get_position(motor_id)
        output_deg = math.degrees(motor_rad / hardware.gear_ratio)
        parts.append(f"{role}#{motor_id}:{output_deg:+.1f}deg")
    return " ".join(parts)


def build_telemetry_observer(
    hardware: HardwareConfig,
    control: ControlConfig,
    source_name: Callable[[], str],
):
    # 按固定间隔打印一行调试信息，避免主循环 500Hz 时刷屏。
    last_print = 0.0

    def observe(loop_index: int, driver_input: DriverInput, state: ControlState, motors: MotorClient) -> None:
        nonlocal last_print
        now = time.monotonic()
        if now - last_print < control.telemetry_interval_s:
            return
        last_print = now

        print(
            "\r"
            f"循环={loop_index:06d} "
            f"模式={MODE_NAMES.get(state.mode, state.mode)} "
            f"输入源={source_name()} "
            f"转向锁={int(state.steering_locked)} "
            f"方向锁={DIRECTION_NAMES.get(state.drive_direction_mode, state.drive_direction_mode)} "
            f"急停={int(driver_input.emergency_stop_button)} "
            f"左摇杆=({driver_input.left_x:+.2f},{driver_input.left_y:+.2f}) "
            f"右摇杆=({driver_input.right_x:+.2f},{driver_input.right_y:+.2f}) "
            f"驱动[{_drive_summary(hardware, motors)}] "
            f"转向[{_steer_summary(hardware, motors)}]",
            end="",
            flush=True,
        )

    return observe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Car control system")
    parser.add_argument("--mock", action="store_true", help="use simulated motor client instead of real hardware")
    parser.add_argument("--input", choices=["neutral", "demo", "gamepad", "remote", "hybrid"], default="demo")
    parser.add_argument("--gamepad-index", type=int, default=0)
    parser.add_argument("--control-profile", choices=["conservative", "normal", "sport"], default="normal")
    parser.add_argument("--hardware-config", default="configs/hardware.json")
    parser.add_argument("--control-config", default="configs/control.json")
    parser.add_argument("--input-config", default="configs/input.json")
    parser.add_argument("--network-config", default="configs/network.json")
    parser.add_argument(
        "--max-loops",
        type=int,
        default=None,
        help="loop count before exit; omit it for continuous gamepad control, use 0 for infinite",
    )
    parser.add_argument("--telemetry", action="store_true", help="print live input and motor targets")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    hardware = load_hardware_config(args.hardware_config)
    control = load_control_config(args.control_config, profile_name=args.control_profile)
    motors = build_motor_client(args, hardware)
    controller = CarController(hardware, control, motors)

    closeables: list[Callable[[], None]] = []
    source_name_provider: Callable[[], str] = lambda: "脚本"

    if args.input == "gamepad":
        gamepad_config = load_gamepad_config(args.input_config)
        input_reader = PygameGamepadInput(gamepad_config, args.gamepad_index)
        input_reader.open()
        closeables.append(input_reader.close)
        input_provider = input_reader.poll
        source_name_provider = lambda: "本地手柄"
    elif args.input == "remote":
        network_config = load_network_config(args.network_config)
        remote_reader = UdpRemoteInput(network_config)
        remote_reader.open()
        closeables.append(remote_reader.close)
        input_provider = remote_reader.poll
        source_name_provider = lambda: remote_reader.last_source_label
    elif args.input == "hybrid":
        gamepad_config = load_gamepad_config(args.input_config)
        network_config = load_network_config(args.network_config)
        local_reader = PygameGamepadInput(gamepad_config, args.gamepad_index)
        remote_reader = UdpRemoteInput(network_config)
        local_reader.open()
        remote_reader.open()
        closeables.append(remote_reader.close)
        closeables.append(local_reader.close)
        hybrid = HybridInputSource(local_reader.poll, remote_reader)
        input_provider = hybrid.poll

        def hybrid_source_name() -> str:
            return hybrid.last_source_label

        source_name_provider = hybrid_source_name
    else:
        input_provider = build_demo_input_provider(args)
        if args.input == "neutral":
            source_name_provider = lambda: "空闲"
        else:
            source_name_provider = lambda: "脚本"

    # 手柄模式默认持续运行，脚本输入默认短跑，方便本地快速检查。
    if args.max_loops is None:
        max_loops = None if args.input in ("gamepad", "remote", "hybrid") else 10
    elif args.max_loops <= 0:
        max_loops = None
    else:
        max_loops = args.max_loops

    observer = None
    if args.telemetry or (args.mock and args.input == "gamepad"):
        observer = build_telemetry_observer(hardware, control, source_name_provider)

    try:
        controller.run(input_provider, max_loops=max_loops, observer=observer)
        if observer is not None:
            print()
    finally:
        for close in closeables:
            close()

    if isinstance(motors, MockMotorClient):
        print("commands:")
        for cmd in motors.commands:
            print(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
