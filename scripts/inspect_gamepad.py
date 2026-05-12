from __future__ import annotations

import argparse
import os
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="实时查看手柄原始轴和按键编号。")
    parser.add_argument("--index", type=int, default=0, help="手柄编号，默认 0。")
    parser.add_argument("--interval", type=float, default=0.2, help="刷新间隔，单位秒。")
    args = parser.parse_args()

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame  # type: ignore
    except ModuleNotFoundError:
        print("未安装 pygame，请先运行：python3 -m pip install pygame")
        return 1

    pygame.init()
    pygame.joystick.init()
    try:
        count = pygame.joystick.get_count()
        if count <= 0:
            print("没有检测到手柄。请先确认 USB/蓝牙已经连接，并被 Ubuntu 识别。")
            return 1
        if args.index < 0 or args.index >= count:
            print(f"手柄编号越界：index={args.index}, 当前检测到 {count} 个手柄。")
            return 1

        joystick = pygame.joystick.Joystick(args.index)
        joystick.init()
        print("=== 手柄原始输入检测 ===")
        print(f"index={args.index}")
        print(f"名称={joystick.get_name()}")
        print(f"轴数量={joystick.get_numaxes()} 按键数量={joystick.get_numbuttons()} 帽键数量={joystick.get_numhats()}")
        print("操作方法：一次只动一个摇杆或按一个键，观察哪个 axis/button 变化。按 Ctrl+C 退出。")
        print("建议记录：左摇杆X、左摇杆Y、右摇杆X、右摇杆Y、模式键、转向锁、前进倒车、急停。")

        while True:
            pygame.event.pump()
            axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
            buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
            hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]

            axis_text = " ".join(f"axis{i}={value:+.2f}" for i, value in enumerate(axes))
            pressed_buttons = [str(i) for i, value in enumerate(buttons) if value]
            button_text = ",".join(pressed_buttons) if pressed_buttons else "-"
            hat_text = " ".join(f"hat{i}={value}" for i, value in enumerate(hats)) if hats else "-"
            print(f"\r{axis_text} | buttons={button_text} | {hat_text}      ", end="", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已退出手柄检测。")
        return 0
    finally:
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
