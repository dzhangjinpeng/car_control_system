from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import shutil
import sys
import time
from pathlib import Path
from typing import TextIO

from .types import DriverInput


@dataclass(frozen=True)
class MotorTelemetry:
    # 电机角色，例如 front_left / rear_right。
    role: str
    # 电机 CAN ID。
    motor_id: int
    # 目标值，驱动轮单位 rad/s，转向轮单位 deg。
    target: float
    # 实测值，驱动轮单位 rad/s，转向轮单位 deg。
    actual: float
    # 目标值和实测值的差值。
    error: float
    # 单位说明。
    unit: str


@dataclass(frozen=True)
class TelemetryFrame:
    # 这一帧的采样时间。
    timestamp: float
    # 主循环编号。
    loop_index: int
    # 当前控制模式名称。
    mode_name: str
    # 当前输入来源。
    input_source: str
    # 转向锁状态。
    steering_locked: bool
    # 方向锁名称。
    drive_direction_name: str
    # 是否触发急停。
    emergency_stop: bool
    # 经过平滑后的摇杆输入。
    driver_input: DriverInput
    # 驱动轮摘要文本。
    drive_summary: str
    # 转向轮摘要文本。
    steer_summary: str
    # 结构化驱动轮遥测。
    drive_motors: list[MotorTelemetry]
    # 结构化转向轮遥测。
    steer_motors: list[MotorTelemetry]
    # 附加状态说明。
    notice: str = ""


class TelemetryJsonlWriter:
    # 把每一帧记录成 JSONL，方便后面离线回看。
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a", encoding="utf-8")

    def write(self, frame: TelemetryFrame) -> None:
        payload = {
            "timestamp": frame.timestamp,
            "loop_index": frame.loop_index,
            "mode_name": frame.mode_name,
            "input_source": frame.input_source,
            "steering_locked": frame.steering_locked,
            "drive_direction_name": frame.drive_direction_name,
            "emergency_stop": frame.emergency_stop,
            "driver_input": asdict(frame.driver_input),
            "drive_summary": frame.drive_summary,
            "steer_summary": frame.steer_summary,
            "drive_motors": [asdict(item) for item in frame.drive_motors],
            "steer_motors": [asdict(item) for item in frame.steer_motors],
            "notice": frame.notice,
        }
        self._stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._stream.flush()

    def close(self) -> None:
        self._stream.close()


class TelemetryConsole:
    # 更适合现场看的控制台面板。
    def __init__(self, stream: TextIO | None = None, use_color: bool | None = None) -> None:
        self.stream = stream or sys.stdout
        self.use_color = self.stream.isatty() if use_color is None else use_color
        self._width = shutil.get_terminal_size(fallback=(120, 30)).columns
        self._rendered_once = False

    def render(self, frame: TelemetryFrame) -> None:
        if self.use_color and self.stream.isatty():
            self._render_dashboard(frame)
        else:
            self.render_plain(frame)

    def render_plain(self, frame: TelemetryFrame) -> None:
        # 纯文本输出适合重定向到文件，也适合不支持 ANSI 的终端。
        self._render_plain(frame)

    def finish(self) -> None:
        if self.stream.isatty():
            self.stream.write("\n")
            self.stream.flush()

    def _render_dashboard(self, frame: TelemetryFrame) -> None:
        self._width = shutil.get_terminal_size(fallback=(120, 30)).columns
        lines = self._build_lines(frame)
        self.stream.write("\x1b[2J\x1b[H")
        self.stream.write("\n".join(lines))
        self.stream.flush()

    def _render_plain(self, frame: TelemetryFrame) -> None:
        self.stream.write(" | ".join(self._plain_parts(frame)) + "\n")
        self.stream.flush()

    def _build_lines(self, frame: TelemetryFrame) -> list[str]:
        width = max(self._width, 96)
        title = self._color("小车状态", "cyan", bold=True)
        top = self._pad_line(f"=== {title} ===", width)
        bottom = "=" * min(width, 120)
        lines = [
            top,
            self._pad_line(
                f"循环: {frame.loop_index:06d}   模式: {self._color(frame.mode_name, 'green')}   "
                f"输入源: {self._color(frame.input_source, 'yellow')}",
                width,
            ),
            self._pad_line(
                f"转向锁: {self._color('开' if frame.steering_locked else '关', 'magenta')}   "
                f"方向锁: {self._color(frame.drive_direction_name, 'blue')}   "
                f"急停: {self._color('是' if frame.emergency_stop else '否', 'red' if frame.emergency_stop else 'green')}",
                width,
            ),
            self._pad_line(
                f"左摇杆: X {frame.driver_input.left_x:+.2f}  Y {frame.driver_input.left_y:+.2f}   "
                f"右摇杆: X {frame.driver_input.right_x:+.2f}  Y {frame.driver_input.right_y:+.2f}",
                width,
            ),
            self._pad_line(f"驱动: {frame.drive_summary}", width),
            self._pad_line(f"转向: {frame.steer_summary}", width),
            self._pad_line("驱动误差: " + self._motor_error_summary(frame.drive_motors), width),
            self._pad_line("转向误差: " + self._motor_error_summary(frame.steer_motors), width),
        ]
        if frame.notice:
            lines.append(self._pad_line(f"提示: {frame.notice}", width))
        lines.append(bottom)
        return lines

    def _plain_parts(self, frame: TelemetryFrame) -> list[str]:
        parts = [
            f"循环={frame.loop_index:06d}",
            f"模式={frame.mode_name}",
            f"输入源={frame.input_source}",
            f"转向锁={'开' if frame.steering_locked else '关'}",
            f"方向锁={frame.drive_direction_name}",
            f"急停={'是' if frame.emergency_stop else '否'}",
            f"左摇杆=({frame.driver_input.left_x:+.2f},{frame.driver_input.left_y:+.2f})",
            f"右摇杆=({frame.driver_input.right_x:+.2f},{frame.driver_input.right_y:+.2f})",
            f"驱动[{frame.drive_summary}]",
            f"转向[{frame.steer_summary}]",
            f"驱动误差[{self._motor_error_summary(frame.drive_motors)}]",
            f"转向误差[{self._motor_error_summary(frame.steer_motors)}]",
        ]
        if frame.notice:
            parts.append(f"提示={frame.notice}")
        return parts

    def _pad_line(self, text: str, width: int) -> str:
        plain = self._strip_ansi(text)
        if len(plain) >= width:
            return text
        return text + " " * (width - len(plain))

    def _color(self, text: str, color: str, bold: bool = False) -> str:
        if not self.use_color:
            return text
        codes = []
        if bold:
            codes.append("1")
        palette = {
            "red": "31",
            "green": "32",
            "yellow": "33",
            "blue": "34",
            "magenta": "35",
            "cyan": "36",
        }
        codes.append(palette.get(color, "0"))
        return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"

    def _strip_ansi(self, text: str) -> str:
        out = []
        in_escape = False
        for char in text:
            if in_escape:
                if char == "m":
                    in_escape = False
                continue
            if char == "\x1b":
                in_escape = True
                continue
            out.append(char)
        return "".join(out)

    def _motor_error_summary(self, motors: list[MotorTelemetry]) -> str:
        if not motors:
            return "无"
        parts = []
        for item in motors:
            parts.append(f"{item.role}#{item.motor_id}:目标{item.target:+.2f}/实测{item.actual:+.2f}/误差{item.error:+.2f}{item.unit}")
        return " ".join(parts)


def build_telemetry_frame(
    loop_index: int,
    mode_name: str,
    input_source: str,
    steering_locked: bool,
    drive_direction_name: str,
    emergency_stop: bool,
    driver_input: DriverInput,
    drive_summary: str,
    steer_summary: str,
    drive_motors: list[MotorTelemetry] | None = None,
    steer_motors: list[MotorTelemetry] | None = None,
    notice: str = "",
) -> TelemetryFrame:
    # 统一组装一帧遥测数据，给控制台和文件日志共用。
    return TelemetryFrame(
        timestamp=time.time(),
        loop_index=loop_index,
        mode_name=mode_name,
        input_source=input_source,
        steering_locked=steering_locked,
        drive_direction_name=drive_direction_name,
        emergency_stop=emergency_stop,
        driver_input=driver_input,
        drive_summary=drive_summary,
        steer_summary=steer_summary,
        drive_motors=drive_motors or [],
        steer_motors=steer_motors or [],
        notice=notice,
    )
