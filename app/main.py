from __future__ import annotations

import argparse
import math
import sys
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
from car_control.api_server import FrontendApiServer
from car_control.controller import CarController
from car_control.gamepad_input import PygameGamepadInput, describe_gamepads
from car_control.keyboard_input import ScriptedInput, neutral_input
from car_control.motor_client import CxxMotorClient, MockMotorClient, MotorClient
from car_control.network_input import HybridInputSource, UdpRemoteInput
from car_control.telemetry import MotorTelemetry, TelemetryConsole, TelemetryJsonlWriter, TelemetryStore, build_telemetry_frame
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


def _drive_telemetry(hardware: HardwareConfig, motors: MotorClient) -> tuple[str, list[MotorTelemetry]]:
    # 驱动轮速度遥测，单位是电机接口使用的 rad/s。
    parts: list[str] = []
    items: list[MotorTelemetry] = []
    for role, motor_id in hardware.drive_motor_roles.items():
        target = motors.get_target_velocity(motor_id)
        actual = motors.get_velocity(motor_id)
        error = target - actual
        parts.append(f"{role}#{motor_id}:目标{target:+.2f}/实测{actual:+.2f}")
        items.append(
            MotorTelemetry(
                role=role,
                motor_id=motor_id,
                target=target,
                actual=actual,
                error=error,
                unit="rad/s",
            )
        )
    return " ".join(parts), items


def _steer_telemetry(hardware: HardwareConfig, motors: MotorClient) -> tuple[str, list[MotorTelemetry]]:
    # 转向电机保存的是电机轴弧度，这里换算回轮端角度，方便肉眼判断。
    parts: list[str] = []
    items: list[MotorTelemetry] = []
    for role, motor_id in hardware.steer_motor_roles.items():
        target_deg = math.degrees(motors.get_target_position(motor_id) / hardware.gear_ratio)
        actual_deg = math.degrees(motors.get_position(motor_id) / hardware.gear_ratio)
        error_deg = target_deg - actual_deg
        parts.append(f"{role}#{motor_id}:目标{target_deg:+.1f}/实测{actual_deg:+.1f}deg")
        items.append(
            MotorTelemetry(
                role=role,
                motor_id=motor_id,
                target=target_deg,
                actual=actual_deg,
                error=error_deg,
                unit="deg",
            )
        )
    return " ".join(parts), items


def build_telemetry_observer(
    hardware: HardwareConfig,
    control: ControlConfig,
    source_name: Callable[[], str],
    link_state: Callable[[], str] | None = None,
    remote_snapshot: Callable[[], tuple[int | None, float | None, bool | None]] | None = None,
    store: TelemetryStore | None = None,
    log_file: str | None = None,
    dashboard: bool = True,
    render_console: bool = True,
    use_color: bool | None = None,
):
    # 按固定间隔刷新面板，避免主循环 500Hz 时刷屏。
    last_print = 0.0
    console = TelemetryConsole(use_color=use_color)
    writer = TelemetryJsonlWriter(log_file) if log_file else None
    link_state_provider = link_state or (lambda: "本地")
    remote_snapshot_provider = remote_snapshot or (lambda: (None, None, None))

    def observe(loop_index: int, driver_input: DriverInput, state: ControlState, motors: MotorClient) -> None:
        nonlocal last_print
        now = time.monotonic()
        if now - last_print < control.telemetry_interval_s:
            return
        last_print = now

        drive_summary, drive_motors = _drive_telemetry(hardware, motors)
        steer_summary, steer_motors = _steer_telemetry(hardware, motors)
        remote_seq, remote_latency_s, remote_stale = remote_snapshot_provider()
        frame = build_telemetry_frame(
            loop_index=loop_index,
            mode_name=MODE_NAMES.get(state.mode, str(state.mode)),
            input_source=source_name(),
            input_link_state=link_state_provider(),
            remote_seq=remote_seq,
            remote_latency_s=remote_latency_s,
            remote_stale=remote_stale,
            steering_locked=state.steering_locked,
            drive_direction_name=DIRECTION_NAMES.get(state.drive_direction_mode, str(state.drive_direction_mode)),
            emergency_stop=driver_input.emergency_stop_button,
            driver_input=driver_input,
            drive_summary=drive_summary,
            steer_summary=steer_summary,
            drive_motors=drive_motors,
            steer_motors=steer_motors,
        )
        if store is not None:
            store.update(frame)
        if writer is not None:
            writer.write(frame)
        if render_console:
            if dashboard:
                console.render(frame)
            else:
                console.render_plain(frame)

    observe.console = console  # type: ignore[attr-defined]
    observe.writer = writer  # type: ignore[attr-defined]

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
    parser.add_argument("--list-gamepads", action="store_true", help="list detected gamepads and exit")
    parser.add_argument("--log-file", default="", help="write telemetry jsonl to this file")
    parser.add_argument("--no-color", action="store_true", help="disable colored telemetry output")
    parser.add_argument("--plain-telemetry", action="store_true", help="use single-line telemetry instead of dashboard")
    parser.add_argument("--api", action="store_true", help="start read-only HTTP API for frontend")
    parser.add_argument("--api-host", default="127.0.0.1", help="frontend API bind host")
    parser.add_argument("--api-port", type=int, default=8765, help="frontend API port")
    parser.add_argument("--api-history-size", type=int, default=200, help="frontend API history buffer size")
    parser.add_argument("--calibration-report", default="logs/calibration.json", help="calibration report path for API")
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

    if args.list_gamepads:
        for line in describe_gamepads():
            print(line)
        return 0

    hardware = load_hardware_config(args.hardware_config)
    control = load_control_config(args.control_config, profile_name=args.control_profile)
    network_config = load_network_config(args.network_config)
    motors = build_motor_client(args, hardware)
    controller = CarController(hardware, control, motors)

    closeables: list[Callable[[], None]] = []
    api_server: FrontendApiServer | None = None
    telemetry_store = TelemetryStore(args.api_history_size) if args.api else None
    source_name_provider: Callable[[], str] = lambda: "脚本"
    link_state_provider: Callable[[], str] = lambda: "本地"
    remote_snapshot_provider: Callable[[], tuple[int | None, float | None, bool | None]] = lambda: (None, None, None)

    if args.input == "gamepad":
        gamepad_config = load_gamepad_config(args.input_config)
        input_reader = PygameGamepadInput(gamepad_config, args.gamepad_index)
        input_reader.open()
        closeables.append(input_reader.close)
        input_provider = input_reader.poll
        source_name_provider = lambda: "本地手柄"
        link_state_provider = lambda: "本地在线"
    elif args.input == "remote":
        remote_reader = UdpRemoteInput(network_config)
        remote_reader.open()
        closeables.append(remote_reader.close)
        input_provider = remote_reader.poll
        source_name_provider = lambda: remote_reader.last_source_label
        link_state_provider = remote_reader.link_state
        remote_snapshot_provider = remote_reader.remote_snapshot
    elif args.input == "hybrid":
        gamepad_config = load_gamepad_config(args.input_config)
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
        link_state_provider = hybrid.link_state
        remote_snapshot_provider = hybrid.remote_snapshot
    else:
        input_provider = build_demo_input_provider(args)
        if args.input == "neutral":
            source_name_provider = lambda: "空闲"
        else:
            source_name_provider = lambda: "脚本"
        link_state_provider = lambda: "本地"

    if args.api:
        api_server = FrontendApiServer(
            args.api_host,
            args.api_port,
            telemetry_store=telemetry_store or TelemetryStore(args.api_history_size),
            hardware=hardware,
            control=control,
            network=network_config,
            calibration_report_path=args.calibration_report,
        )

    # 手柄模式默认持续运行，脚本输入默认短跑，方便本地快速检查。
    if args.max_loops is None:
        max_loops = None if args.input in ("gamepad", "remote", "hybrid") else 10
    elif args.max_loops <= 0:
        max_loops = None
    else:
        max_loops = args.max_loops

    observer = None
    if args.telemetry or args.api or (args.mock and args.input == "gamepad"):
        dashboard = sys.stdout.isatty() and not args.plain_telemetry
        observer = build_telemetry_observer(
            hardware,
            control,
            source_name_provider,
            link_state_provider,
            remote_snapshot_provider,
            store=telemetry_store,
            log_file=args.log_file or None,
            dashboard=dashboard,
            render_console=args.telemetry,
            use_color=sys.stdout.isatty() and not args.no_color,
        )
        if api_server is not None:
            api_server.start()
        if args.api:
            print(f"frontend api: {api_server.url if api_server is not None else 'n/a'}")

    try:
        controller.run(input_provider, max_loops=max_loops, observer=observer)
        if observer is not None:
            print()
    finally:
        if api_server is not None:
            api_server.close()
        for close in closeables:
            close()
        if observer is not None:
            console = getattr(observer, "console", None)
            writer = getattr(observer, "writer", None)
            if hasattr(console, "finish"):
                console.finish()
            if hasattr(writer, "close"):
                writer.close()

    if isinstance(motors, MockMotorClient):
        print("commands:")
        for cmd in motors.commands:
            print(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
