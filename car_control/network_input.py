from __future__ import annotations

from dataclasses import dataclass
import socket
import time
from typing import Callable

from .config import NetworkConfig
from .remote_protocol import RemoteControlPacket
from .types import DriverInput


@dataclass
class _LatestRemoteFrame:
    packet: RemoteControlPacket
    received_monotonic: float


class UdpRemoteInput:
    # 远程输入接收器，只负责拿最新一帧，不直接碰电机。
    def __init__(self, config: NetworkConfig) -> None:
        self.config = config
        self._socket: socket.socket | None = None
        self._latest: _LatestRemoteFrame | None = None
        self.last_source_label = "远程"

    def open(self) -> None:
        # 绑定 UDP 端口，接收电脑端发送的手柄状态。
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.config.bind_host, self.config.port))
        sock.settimeout(self.config.poll_timeout_s)
        self._socket = sock

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
        self._socket = None
        self._latest = None

    def latest_packet(self) -> RemoteControlPacket | None:
        # 先把 socket 缓冲里的包都读空，只保留最新的一帧。
        if self._socket is None:
            raise RuntimeError("remote input is not open")

        while True:
            try:
                data, _addr = self._socket.recvfrom(4096)
            except TimeoutError:
                break
            except BlockingIOError:
                break
            except socket.timeout:
                break
            packet = RemoteControlPacket.from_wire_bytes(data)
            self._latest = _LatestRemoteFrame(packet=packet, received_monotonic=time.monotonic())

        return self._latest.packet if self._latest is not None else None

    def latest_age_s(self) -> float | None:
        if self._latest is None:
            return None
        return time.monotonic() - self._latest.received_monotonic

    def latest_seq(self) -> int | None:
        if self._latest is None:
            return None
        return self._latest.packet.seq

    def link_state(self) -> str:
        # 给遥测面板和前端用，直接返回远程链路的健康状态。
        if self._latest is None:
            return "远程空闲"
        age_s = self.latest_age_s()
        if age_s is None:
            return "远程空闲"
        if not self._latest.packet.active:
            return "远程无效"
        if age_s > self.config.timeout_s:
            return "远程超时回退"
        return "远程在线"

    def remote_snapshot(self) -> tuple[int | None, float | None, bool | None]:
        # 一次性返回远程序号、时延和是否过期，方便遥测层直接取值。
        return self.latest_seq(), self.latest_age_s(), self.is_stale()

    def is_stale(self) -> bool | None:
        if self._latest is None:
            return None
        age_s = self.latest_age_s()
        if age_s is None:
            return None
        return age_s > self.config.timeout_s

    def poll(self) -> DriverInput:
        # 如果没有新包或者包已经过期，就回到中位，避免车继续跑。
        packet = self.latest_packet()
        if packet is None:
            self.last_source_label = "远程(空闲)"
            return DriverInput()
        age_s = self.latest_age_s()
        if age_s is None or age_s > self.config.timeout_s or not packet.active:
            self.last_source_label = "远程(超时)"
            return DriverInput()
        self.last_source_label = "远程"
        return packet.driver_input


class HybridInputSource:
    # 同时保留本地手柄和远程输入。
    def __init__(
        self,
        local_provider: Callable[[], DriverInput],
        remote_input: UdpRemoteInput,
    ) -> None:
        self.local_provider = local_provider
        self.remote_input = remote_input
        self.last_source_label = "本地手柄"
        self._last_link_state = "本地手柄"
        self._last_remote_snapshot: tuple[int | None, float | None, bool | None] = (None, None, None)

    def _stale_from_age(self, age_s: float | None) -> bool | None:
        # 测试桩不一定实现 is_stale()，这里直接根据时延判断。
        if age_s is None:
            return None
        return age_s > self.remote_input.config.timeout_s

    def poll(self) -> DriverInput:
        # 本地急停永远优先，其次才考虑远程接管。
        local_input = self.local_provider()
        remote_packet = self.remote_input.latest_packet()
        age_s = self.remote_input.latest_age_s()

        if local_input.emergency_stop_button:
            self.last_source_label = "本地急停"
            self._last_link_state = "本地急停"
            self._last_remote_snapshot = (
                remote_packet.seq if remote_packet is not None else None,
                age_s,
                self._stale_from_age(age_s),
            )
            return local_input

        if remote_packet is None or age_s is None:
            self.last_source_label = "本地手柄"
            self._last_link_state = "本地手柄"
            self._last_remote_snapshot = (None, None, None)
            return local_input

        if not remote_packet.active or age_s > self.remote_input.config.timeout_s:
            self.last_source_label = "本地手柄"
            self._last_link_state = "远程超时回退" if age_s > self.remote_input.config.timeout_s else "远程无效"
            self._last_remote_snapshot = (
                remote_packet.seq,
                age_s,
                self._stale_from_age(age_s),
            )
            return local_input

        remote_input = remote_packet.driver_input
        self.last_source_label = "远程接管"
        self._last_link_state = "远程接管"
        self._last_remote_snapshot = (
            remote_packet.seq,
            age_s,
            self._stale_from_age(age_s),
        )
        return DriverInput(
            left_x=remote_input.left_x,
            left_y=remote_input.left_y,
            right_x=remote_input.right_x,
            right_y=remote_input.right_y,
            mode_button=remote_input.mode_button or local_input.mode_button,
            steering_lock_button=remote_input.steering_lock_button or local_input.steering_lock_button,
            drive_direction_button=remote_input.drive_direction_button or local_input.drive_direction_button,
            emergency_stop_button=remote_input.emergency_stop_button or local_input.emergency_stop_button,
        )

    def link_state(self) -> str:
        # 给遥测面板用，返回上一次采样时判断出来的链路状态。
        return self._last_link_state

    def remote_snapshot(self) -> tuple[int | None, float | None, bool | None]:
        # 给遥测面板返回上一次采样时的远程序号、时延和过期状态。
        return self._last_remote_snapshot
