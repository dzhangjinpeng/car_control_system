from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.api_server import FrontendApiServer
from car_control.config import load_control_config, load_hardware_config, load_network_config
from car_control.telemetry import TelemetryStore, build_telemetry_frame
from car_control.types import DriverInput


class ApiServerTest(unittest.TestCase):
    def test_endpoints_expose_latest_telemetry_and_configs(self) -> None:
        hardware = load_hardware_config()
        control = load_control_config()
        network = load_network_config()
        store = TelemetryStore(max_history=4)

        frame = build_telemetry_frame(
            loop_index=3,
            mode_name="mode1",
            input_source="本地手柄",
            input_link_state="本地在线",
            remote_seq=9,
            remote_latency_s=0.021,
            remote_stale=False,
            steering_locked=False,
            drive_direction_name="自动",
            emergency_stop=False,
            driver_input=DriverInput(left_y=-0.4),
            drive_summary="rear_right#1:+0.10",
            steer_summary="front_left#6:+2.0deg",
        )
        store.update(frame)
        store.update(
            build_telemetry_frame(
                loop_index=4,
                mode_name="mode2",
                input_source="远程",
                input_link_state="远程接管",
                remote_seq=10,
                remote_latency_s=0.018,
                remote_stale=False,
                steering_locked=True,
                drive_direction_name="只前进",
                emergency_stop=False,
                driver_input=DriverInput(left_y=0.8),
                drive_summary="rear_right#1:+0.30",
                steer_summary="front_left#6:+0.5deg",
            )
        )

        with TemporaryDirectory() as tmpdir:
            calibration_path = Path(tmpdir) / "calibration.json"
            calibration_path.write_text(json.dumps({"ok": True, "notes": ["ready"]}), encoding="utf-8")

            server = FrontendApiServer(
                "127.0.0.1",
                0,
                telemetry_store=store,
                hardware=hardware,
                control=control,
                network=network,
                calibration_report_path=calibration_path,
            )
            server.start()
            try:
                time.sleep(0.05)
                base = server.url

                health = self._get_json(f"{base}/api/v1/health")
                latest = self._get_json(f"{base}/api/v1/telemetry/latest")
                history = self._get_json(f"{base}/api/v1/telemetry/history?limit=1")
                hardware_payload = self._get_json(f"{base}/api/v1/config/hardware")
                calibration = self._get_json(f"{base}/api/v1/calibration/latest")
                meta = self._get_json(f"{base}/api/v1/meta")

                self.assertTrue(health["ok"])
                self.assertEqual(health["data"]["schema_version"], 1)
                self.assertEqual(health["data"]["mode_name"], "mode2")
                self.assertIn("bridge_library_exists", health["data"]["startup_checks"])
                self.assertIn("config_issues", health["data"])
                self.assertIsInstance(health["data"]["startup_checks"]["ok"], bool)
                self.assertIsInstance(health["data"]["config_issues"], list)
                self.assertEqual(latest["data"]["loop_index"], 4)
                self.assertEqual(history["data"][0]["loop_index"], 4)
                self.assertIn("front_left", hardware_payload["data"]["drive_motor_roles"])
                self.assertEqual(calibration["data"]["notes"], ["ready"])
                self.assertEqual(meta["data"]["schema_version"], 1)
            finally:
                server.close()

    def _get_json(self, url: str) -> dict:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
