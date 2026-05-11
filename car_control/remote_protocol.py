from __future__ import annotations

from dataclasses import dataclass
import json

from .types import DriverInput


@dataclass(frozen=True)
class RemoteControlPacket:
    # 远程包的序号，用于调试和丢包分析。
    seq: int
    # 发送时间戳，单位秒，由发送端生成。
    timestamp: float
    # 是否启用这帧输入，False 时板子应视为无效输入。
    active: bool
    # 实际控制输入。
    driver_input: DriverInput

    def to_wire_bytes(self) -> bytes:
        # 用 JSON 作为远程协议格式，调试最直观。
        payload = {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "active": self.active,
            "left_x": self.driver_input.left_x,
            "left_y": self.driver_input.left_y,
            "right_x": self.driver_input.right_x,
            "right_y": self.driver_input.right_y,
            "mode_button": self.driver_input.mode_button,
            "steering_lock_button": self.driver_input.steering_lock_button,
            "drive_direction_button": self.driver_input.drive_direction_button,
            "emergency_stop_button": self.driver_input.emergency_stop_button,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def from_wire_bytes(data: bytes) -> RemoteControlPacket:
        # 解析远程 JSON 包，缺字段时直接报错，避免静默误控。
        raw = json.loads(data.decode("utf-8"))
        driver_input = DriverInput(
            left_x=float(raw.get("left_x", 0.0)),
            left_y=float(raw.get("left_y", 0.0)),
            right_x=float(raw.get("right_x", 0.0)),
            right_y=float(raw.get("right_y", 0.0)),
            mode_button=bool(raw.get("mode_button", False)),
            steering_lock_button=bool(raw.get("steering_lock_button", False)),
            drive_direction_button=bool(raw.get("drive_direction_button", False)),
            emergency_stop_button=bool(raw.get("emergency_stop_button", False)),
        )
        return RemoteControlPacket(
            seq=int(raw.get("seq", 0)),
            timestamp=float(raw.get("timestamp", 0.0)),
            active=bool(raw.get("active", True)),
            driver_input=driver_input,
        )
