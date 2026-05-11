from __future__ import annotations

import argparse
import socket
import time

from car_control.config import load_gamepad_config
from car_control.gamepad_input import PygameGamepadInput, describe_gamepads
from car_control.keyboard_input import ScriptedInput, neutral_input
from car_control.remote_protocol import RemoteControlPacket
from car_control.types import DriverInput


def build_input_provider(args: argparse.Namespace):
    # 发送器只负责把本机手柄状态变成远程包。
    if args.input == "neutral":
        return neutral_input, None
    if args.input == "demo":
        frames = [
            DriverInput(left_y=-1.0),
            DriverInput(left_y=-1.0),
            DriverInput(left_y=-1.0, left_x=0.6),
            DriverInput(left_y=-1.0, drive_direction_button=True),
            DriverInput(left_y=1.0),
            DriverInput(emergency_stop_button=True),
        ]
        scripted = ScriptedInput(frames)
        return scripted.next, None
    if args.input == "gamepad":
        gamepad_config = load_gamepad_config(args.input_config)
        gamepad = PygameGamepadInput(gamepad_config, args.gamepad_index)
        gamepad.open()
        return gamepad.poll, gamepad
    raise ValueError(f"unsupported input mode: {args.input}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remote control sender")
    parser.add_argument("--host", default="", help="board IP or hostname")
    parser.add_argument("--port", type=int, default=23333)
    parser.add_argument("--input", choices=["neutral", "demo", "gamepad"], default="gamepad")
    parser.add_argument("--input-config", default="configs/input.json")
    parser.add_argument("--gamepad-index", type=int, default=0)
    parser.add_argument("--hz", type=float, default=30.0, help="send rate in Hz")
    parser.add_argument("--max-seconds", type=float, default=0.0, help="optional exit timeout, 0 means run forever")
    parser.add_argument("--list-gamepads", action="store_true", help="list detected gamepads and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_gamepads:
        for line in describe_gamepads():
            print(line)
        return 0
    if not args.host:
        raise SystemExit("缺少 --host，示例：python remote_control_sender.py --host 192.168.1.50 --input gamepad")

    input_provider, closer = build_input_provider(args)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0
    period_s = 1.0 / max(1.0, args.hz)
    deadline = None if args.max_seconds <= 0 else time.monotonic() + args.max_seconds

    try:
        while deadline is None or time.monotonic() < deadline:
            start = time.monotonic()
            driver_input = input_provider()
            packet = RemoteControlPacket(
                seq=seq,
                timestamp=time.time(),
                active=True,
                driver_input=driver_input,
            )
            sock.sendto(packet.to_wire_bytes(), (args.host, args.port))
            seq += 1
            sleep_s = period_s - (time.monotonic() - start)
            if sleep_s > 0:
                time.sleep(sleep_s)
    except KeyboardInterrupt:
        stop_packet = RemoteControlPacket(
            seq=seq,
            timestamp=time.time(),
            active=True,
            driver_input=DriverInput(emergency_stop_button=True),
        )
        sock.sendto(stop_packet.to_wire_bytes(), (args.host, args.port))
    finally:
        if closer is not None:
            closer.close()
        sock.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
