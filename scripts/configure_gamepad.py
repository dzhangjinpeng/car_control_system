from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Callable


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sample_axis(joystick, pygame, duration_s: float) -> tuple[int, float]:
    # 在采样窗口里找变化幅度最大的轴，用来判断当前动作对应哪个 axis。
    axis_count = joystick.get_numaxes()
    baseline = [joystick.get_axis(i) for i in range(axis_count)]
    max_delta = [0.0 for _ in range(axis_count)]
    end_time = time.monotonic() + duration_s
    while time.monotonic() < end_time:
        pygame.event.pump()
        for index in range(axis_count):
            delta = joystick.get_axis(index) - baseline[index]
            if abs(delta) > abs(max_delta[index]):
                max_delta[index] = delta
        time.sleep(0.02)

    best_index = max(range(axis_count), key=lambda item: abs(max_delta[item]))
    return best_index, max_delta[best_index]


def _sample_button(joystick, pygame, duration_s: float) -> int:
    # 在采样窗口里返回第一个被按下的按键编号。
    end_time = time.monotonic() + duration_s
    while time.monotonic() < end_time:
        pygame.event.pump()
        for index in range(joystick.get_numbuttons()):
            if joystick.get_button(index):
                return index
        time.sleep(0.02)
    raise RuntimeError("没有检测到按键，请重新运行并按住目标按键。")


def _prompt_axis(label: str, action: str, sampler: Callable[[], tuple[int, float]]) -> int:
    input(f"\n{label}：请{action}，然后按 Enter 开始采样。")
    print("采样中，请保持动作 2 秒...")
    axis, delta = sampler()
    print(f"检测结果：{label} = axis{axis}，变化量 {delta:+.2f}")
    return axis


def _prompt_button(label: str, sampler: Callable[[], int]) -> int:
    input(f"\n{label}：请按住目标按键，然后按 Enter 开始采样。")
    print("采样中，请保持按键 2 秒...")
    button = sampler()
    print(f"检测结果：{label} = button{button}")
    return button


def main() -> int:
    parser = argparse.ArgumentParser(description="交互式生成手柄映射配置。")
    parser.add_argument("--index", type=int, default=0, help="手柄编号，默认 0。")
    parser.add_argument("--config", default="configs/input.json", help="要写入的 input.json 路径。")
    parser.add_argument("--duration", type=float, default=2.0, help="每一步采样秒数。")
    args = parser.parse_args()

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame  # type: ignore
    except ModuleNotFoundError:
        print("未安装 pygame，请先运行：python3 -m pip install pygame")
        return 1

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"找不到配置文件：{config_path}")
        return 1

    pygame.init()
    pygame.joystick.init()
    try:
        count = pygame.joystick.get_count()
        if count <= 0:
            print("没有检测到手柄。")
            return 1
        if args.index < 0 or args.index >= count:
            print(f"手柄编号越界：index={args.index}, 当前检测到 {count} 个手柄。")
            return 1

        joystick = pygame.joystick.Joystick(args.index)
        joystick.init()
        print("=== 手柄映射向导 ===")
        print(f"名称={joystick.get_name()} 轴={joystick.get_numaxes()} 按键={joystick.get_numbuttons()}")
        print("每一步只动一个摇杆方向或只按一个键。写入后会关闭 auto_detect，避免自动映射覆盖现场结果。")

        axis_sampler = lambda: _sample_axis(joystick, pygame, args.duration)
        button_sampler = lambda: _sample_button(joystick, pygame, args.duration)

        left_x = _prompt_axis("左摇杆 X", "向右推左摇杆", axis_sampler)
        left_y = _prompt_axis("左摇杆 Y", "向上推左摇杆", axis_sampler)
        right_x = _prompt_axis("右摇杆 X", "向右推右摇杆", axis_sampler)
        right_y = _prompt_axis("右摇杆 Y", "向上推右摇杆", axis_sampler)
        mode_button = _prompt_button("模式切换键", button_sampler)
        steering_lock_button = _prompt_button("转向锁定键", button_sampler)
        drive_direction_button = _prompt_button("前进/倒车键", button_sampler)
        emergency_stop_button = _prompt_button("急停键", button_sampler)

        data = _read_json(config_path)
        data["auto_detect"] = False
        data["left_x_axis"] = left_x
        data["left_y_axis"] = left_y
        data["right_x_axis"] = right_x
        data["right_y_axis"] = right_y
        data["mode_button"] = mode_button
        data["steering_lock_button"] = steering_lock_button
        data["drive_direction_button"] = drive_direction_button
        data["emergency_stop_button"] = emergency_stop_button
        _write_json(config_path, data)

        print(f"\n已写入：{config_path}")
        print("下一步验证：")
        print("  python3 car_control_system.py --mock --input gamepad --gamepad-index 0 --telemetry")
        return 0
    finally:
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
