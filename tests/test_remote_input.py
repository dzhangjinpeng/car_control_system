from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_control.network_input import HybridInputSource
from car_control.remote_protocol import RemoteControlPacket
from car_control.types import DriverInput


class _FakeRemote:
    def __init__(self, packet: RemoteControlPacket | None, age_s: float | None, timeout_s: float = 0.2) -> None:
        self._packet = packet
        self._age_s = age_s
        self.config = SimpleNamespace(timeout_s=timeout_s)
        self.last_source_label = "远程"

    def latest_packet(self) -> RemoteControlPacket | None:
        return self._packet

    def latest_age_s(self) -> float | None:
        return self._age_s


class RemoteInputTest(unittest.TestCase):
    def test_packet_roundtrip_preserves_fields(self) -> None:
        packet = RemoteControlPacket(
            seq=42,
            timestamp=123.456,
            active=True,
            driver_input=DriverInput(
                left_x=0.1,
                left_y=-0.2,
                right_x=0.3,
                right_y=-0.4,
                mode_button=True,
                steering_lock_button=True,
                drive_direction_button=True,
                emergency_stop_button=True,
            ),
        )

        restored = RemoteControlPacket.from_wire_bytes(packet.to_wire_bytes())

        self.assertEqual(restored.seq, 42)
        self.assertAlmostEqual(restored.timestamp, 123.456)
        self.assertTrue(restored.active)
        self.assertAlmostEqual(restored.driver_input.left_x, 0.1)
        self.assertTrue(restored.driver_input.emergency_stop_button)

    def test_hybrid_prefers_remote_when_fresh(self) -> None:
        packet = RemoteControlPacket(
            seq=1,
            timestamp=1.0,
            active=True,
            driver_input=DriverInput(left_y=-1.0, drive_direction_button=True),
        )
        hybrid = HybridInputSource(lambda: DriverInput(left_y=0.5, steering_lock_button=True), _FakeRemote(packet, 0.05))

        result = hybrid.poll()

        self.assertAlmostEqual(result.left_y, -1.0)
        self.assertTrue(result.steering_lock_button)
        self.assertTrue(result.drive_direction_button)
        self.assertEqual(hybrid.last_source_label, "远程接管")
        self.assertEqual(hybrid.link_state(), "远程接管")
        self.assertEqual(hybrid.remote_snapshot(), (1, 0.05, False))

    def test_hybrid_falls_back_to_local_when_remote_stale(self) -> None:
        packet = RemoteControlPacket(
            seq=1,
            timestamp=1.0,
            active=True,
            driver_input=DriverInput(left_y=-1.0),
        )
        hybrid = HybridInputSource(lambda: DriverInput(left_y=0.5), _FakeRemote(packet, 1.0))

        result = hybrid.poll()

        self.assertAlmostEqual(result.left_y, 0.5)
        self.assertEqual(hybrid.last_source_label, "本地手柄")
        self.assertEqual(hybrid.link_state(), "远程超时回退")
        self.assertEqual(hybrid.remote_snapshot(), (1, 1.0, True))

    def test_hybrid_local_emergency_stop_wins(self) -> None:
        packet = RemoteControlPacket(
            seq=1,
            timestamp=1.0,
            active=True,
            driver_input=DriverInput(left_y=-1.0, emergency_stop_button=False),
        )
        hybrid = HybridInputSource(lambda: DriverInput(left_y=0.5, emergency_stop_button=True), _FakeRemote(packet, 0.05))

        result = hybrid.poll()

        self.assertTrue(result.emergency_stop_button)
        self.assertAlmostEqual(result.left_y, 0.5)
        self.assertEqual(hybrid.last_source_label, "本地急停")


if __name__ == "__main__":
    unittest.main()
