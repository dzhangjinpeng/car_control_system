from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.telemetry import MotorTelemetry, TelemetryConsole, TelemetryJsonlWriter, build_telemetry_frame
from car_control.types import DriverInput


class TelemetryTest(unittest.TestCase):
    def test_jsonl_writer_serializes_frame(self) -> None:
        frame = build_telemetry_frame(
            loop_index=12,
            mode_name="mode1",
            input_source="本地手柄",
            input_link_state="本地在线",
            remote_seq=7,
            remote_latency_s=0.012,
            remote_stale=False,
            steering_locked=True,
            drive_direction_name="自动",
            emergency_stop=False,
            driver_input=DriverInput(left_x=0.1, left_y=-0.5),
            drive_summary="rear_right#1:+0.20",
            steer_summary="front_left#6:+10.0deg",
            drive_motors=[
                MotorTelemetry("rear_right", 1, target=0.2, actual=0.1, error=0.1, unit="rad/s")
            ],
            steer_motors=[
                MotorTelemetry("front_left", 6, target=10.0, actual=9.5, error=0.5, unit="deg")
            ],
            notice="ok",
        )

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "telemetry.jsonl"
            writer = TelemetryJsonlWriter(path)
            writer.write(frame)
            writer.close()

            payload = json.loads(path.read_text(encoding="utf-8").strip())

        self.assertEqual(payload["loop_index"], 12)
        self.assertEqual(payload["mode_name"], "mode1")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["input_link_state"], "本地在线")
        self.assertEqual(payload["remote_seq"], 7)
        self.assertAlmostEqual(payload["remote_latency_s"], 0.012)
        self.assertFalse(payload["remote_stale"])
        self.assertEqual(payload["driver_input"]["left_x"], 0.1)
        self.assertEqual(payload["drive_motors"][0]["role"], "rear_right")
        self.assertEqual(payload["steer_motors"][0]["error"], 0.5)
        self.assertEqual(payload["notice"], "ok")

    def test_plain_console_render_contains_key_fields(self) -> None:
        frame = build_telemetry_frame(
            loop_index=1,
            mode_name="mode2",
            input_source="远程",
            input_link_state="远程接管",
            remote_seq=99,
            remote_latency_s=0.045,
            remote_stale=False,
            steering_locked=False,
            drive_direction_name="只前进",
            emergency_stop=True,
            driver_input=DriverInput(left_y=1.0),
            drive_summary="rear_right#1:+0.00",
            steer_summary="front_left#6:+0.0deg",
            drive_motors=[
                MotorTelemetry("rear_right", 1, target=0.0, actual=0.0, error=0.0, unit="rad/s")
            ],
            steer_motors=[
                MotorTelemetry("front_left", 6, target=0.0, actual=0.0, error=0.0, unit="deg")
            ],
        )

        buffer = io.StringIO()
        console = TelemetryConsole(stream=buffer, use_color=False)
        console.render_plain(frame)
        text = buffer.getvalue()

        self.assertIn("mode2", text)
        self.assertIn("远程", text)
        self.assertIn("只前进", text)
        self.assertIn("急停=是", text)
        self.assertIn("目标", text)


if __name__ == "__main__":
    unittest.main()
