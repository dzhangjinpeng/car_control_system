#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from car_control.config import HardwareConfig, load_hardware_config
from car_control.motor_client import CxxMotorClient, MockMotorClient, MotorClient


def parse_args() -> argparse.Namespace:
    # 这个脚本只做硬件校准，不改控制逻辑本身。
    parser = argparse.ArgumentParser(description="Hardware calibration wizard")
    parser.add_argument("--hardware-config", default="configs/hardware.json")
    parser.add_argument("--mock", action="store_true", help="use mock motor client")
    parser.add_argument("--probe", action="store_true", help="print live motor status")
    parser.add_argument("--verify", action="store_true", help="check config consistency and live response")
    parser.add_argument("--calibrate-drive", action="store_true", help="calibrate drive motor direction")
    parser.add_argument("--calibrate-steer", action="store_true", help="calibrate steering zero")
    parser.add_argument("--write-config", default="", help="write updated hardware config to this path")
    parser.add_argument("--pulse-speed", type=float, default=0.2, help="drive pulse speed in rad/s")
    parser.add_argument("--pulse-seconds", type=float, default=0.8, help="drive pulse duration in seconds")
    parser.add_argument("--save-flash", action="store_true", help="save steering zero to flash")
    parser.add_argument("--all", action="store_true", help="run probe + drive + steer steps")
    return parser.parse_args()


def build_motor_client(hardware: HardwareConfig, mock: bool) -> MotorClient:
    # mock 模式只验证流程，不碰真实硬件。
    if mock:
        return MockMotorClient()
    return CxxMotorClient(hardware.bridge_library, hardware.serial_number, hardware.nom_baud, hardware.dat_baud)


def prompt_yes_no(message: str, default: bool = False) -> bool:
    # 现场确认用，避免误操作。
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        reply = input(f"{message} {suffix} ").strip().lower()
        if not reply:
            return default
        if reply in {"y", "yes"}:
            return True
        if reply in {"n", "no"}:
            return False


def print_probe(hardware: HardwareConfig, motors: MotorClient) -> None:
    # 打印当前所有电机的实时反馈，方便先确认 ID 和通讯是否都正常。
    print("\n=== 电机回显 ===")
    for motor_id in hardware.motor_ids:
        try:
            pos = motors.get_position(motor_id)
            vel = motors.get_velocity(motor_id)
            tau = motors.get_tau(motor_id)
            print(f"ID {motor_id:02d}: pos={pos:+.3f} rad vel={vel:+.3f} rad/s tau={tau:+.3f} Nm")
        except Exception as exc:
            print(f"ID {motor_id:02d}: 读取失败 -> {exc}")


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


def print_validation_report(hardware: HardwareConfig) -> bool:
    # 让用户一眼看到配置是否自洽。
    issues = validate_hardware_config(hardware)
    print("\n=== 配置校验 ===")
    if not issues:
        print("PASS: hardware.json 自洽")
        print(f"驱动轮 ID: {hardware.drive_motor_ids}")
        print(f"转向轮 ID: {hardware.steer_motor_ids}")
        print(f"驱动反向 ID: {hardware.inverted_drive_motor_ids}")
        return True

    print("FAIL: hardware.json 有问题")
    for issue in issues:
        print(f"- {issue}")
    return False


def stop_drive_motors(hardware: HardwareConfig, motors: MotorClient) -> None:
    # 任何校准前都先把驱动轮停掉。
    for motor_id in hardware.drive_motor_ids:
        try:
            motors.control_vel(motor_id, 0.0)
        except Exception:
            pass


def verify_live_response(hardware: HardwareConfig, motors: MotorClient) -> bool:
    # 检查硬件是否真的能读、能写、能响应。
    print("\n=== 在线响应检查 ===")
    ok = True
    for motor_id in hardware.motor_ids:
        try:
            pos = motors.get_position(motor_id)
            vel = motors.get_velocity(motor_id)
            tau = motors.get_tau(motor_id)
            print(f"PASS: ID {motor_id:02d} 响应正常 pos={pos:+.3f} vel={vel:+.3f} tau={tau:+.3f}")
        except Exception as exc:
            ok = False
            print(f"FAIL: ID {motor_id:02d} 无响应 -> {exc}")
    return ok


def calibrate_drive_direction(hardware: HardwareConfig, motors: MotorClient, pulse_speed: float, pulse_seconds: float) -> list[int]:
    # 通过低速点动判断哪个驱动电机需要反向。
    print("\n=== 驱动方向校准 ===")
    print("请把车架支起来，确保轮子离地。")
    print("接下来会一次只点动一个驱动电机，确认轮子正向转动时是不是在推车前进。")
    if not prompt_yes_no("确认已经做好安全准备了吗？", default=False):
        return list(hardware.inverted_drive_motor_ids)

    inverted = []
    for motor_id in hardware.drive_motor_ids:
        role = next((name for name, value in hardware.drive_motor_roles.items() if value == motor_id), str(motor_id))
        print(f"\n准备点动驱动电机 {motor_id} ({role})")
        if not prompt_yes_no("开始点动吗？", default=True):
            continue
        try:
            motors.control_vel(motor_id, pulse_speed)
            time.sleep(pulse_seconds)
        finally:
            motors.control_vel(motor_id, 0.0)

        print("请观察这个轮子的实际转向。")
        print("输入 y = 正向正确，n = 反向需要取反，s = 跳过")
        while True:
            answer = input("结果 [y/n/s]: ").strip().lower()
            if answer in {"y", "yes"}:
                break
            if answer in {"n", "no"}:
                inverted.append(motor_id)
                break
            if answer in {"s", "skip", ""}:
                break
            print("请输入 y / n / s")

    print("\n驱动反向列表建议值：", inverted)
    return inverted


def calibrate_steer_zero(hardware: HardwareConfig, motors: MotorClient, save_flash: bool) -> None:
    # 让用户把四个转向轮人工摆正，然后把当前角度写成零点。
    print("\n=== 转向零点校准 ===")
    print("请把四个转向轮手动摆正，再继续。")
    if not prompt_yes_no("确认轮子已经摆正了吗？", default=False):
        return

    for motor_id in hardware.steer_motor_ids:
        role = next((name for name, value in hardware.steer_motor_roles.items() if value == motor_id), str(motor_id))
        print(f"校准转向电机 {motor_id} ({role})")
        motors.set_zero_position(motor_id)
        if save_flash:
            motors.save_motor_param(motor_id)


def write_hardware_config(path: str, hardware: HardwareConfig, inverted_drive_motor_ids: list[int]) -> None:
    # 只更新可安全自动生成的字段，不乱动原始 ID 映射。
    payload = asdict(hardware)
    payload["inverted_drive_motor_ids"] = inverted_drive_motor_ids
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写出新配置: {output_path}")


def main() -> int:
    args = parse_args()
    hardware = load_hardware_config(args.hardware_config)
    motors = build_motor_client(hardware, args.mock)

    run_all = args.all or not any([args.probe, args.verify, args.calibrate_drive, args.calibrate_steer])

    try:
        motors.open()
        motors.enable_all()
        print("电机桥已打开并使能。")

        if args.probe or run_all:
            print_probe(hardware, motors)

        if args.verify or run_all:
            config_ok = print_validation_report(hardware)
            live_ok = verify_live_response(hardware, motors)
            if config_ok and live_ok:
                print("\nPASS: 基础校验通过。")
                print("下一步如果要确认轮子方向和零点，再跑校准模式。")
            else:
                print("\nFAIL: 先把上面的错误修完，再继续。")

        inverted_drive_motor_ids = list(hardware.inverted_drive_motor_ids)
        if args.calibrate_drive or run_all:
            inverted_drive_motor_ids = calibrate_drive_direction(hardware, motors, args.pulse_speed, args.pulse_seconds)

        if args.calibrate_steer or run_all:
            calibrate_steer_zero(hardware, motors, save_flash=args.save_flash)

        if args.write_config:
            write_hardware_config(args.write_config, hardware, inverted_drive_motor_ids)
        elif inverted_drive_motor_ids != list(hardware.inverted_drive_motor_ids):
            print("\n如果你想把新的驱动反向列表保存下来，再加：")
            print("  --write-config configs/hardware.local.json")

    finally:
        try:
            stop_drive_motors(hardware, motors)
            motors.disable_all()
        finally:
            motors.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
