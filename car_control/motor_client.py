from __future__ import annotations

from dataclasses import dataclass, field
import ctypes
from pathlib import Path
from typing import Dict, List, Protocol


class MotorClient(Protocol):
    """Small contract used by the controller and mode logic."""
    def open(self) -> None:
        ...

    def close(self) -> None:
        ...

    def enable_all(self) -> None:
        ...

    def disable_all(self) -> None:
        ...

    def control_vel(self, motor_id: int, velocity: float) -> None:
        ...

    def control_pos_vel(self, motor_id: int, position: float, velocity: float) -> None:
        ...

    def get_position(self, motor_id: int) -> float:
        ...

    def get_velocity(self, motor_id: int) -> float:
        ...

    def get_tau(self, motor_id: int) -> float:
        ...


@dataclass
class MockMotorClient:
    # 纯内存替身，用于本地逻辑测试和 demo 运行。
    positions: Dict[int, float] = field(default_factory=dict)
    velocities: Dict[int, float] = field(default_factory=dict)
    torques: Dict[int, float] = field(default_factory=dict)
    commands: List[str] = field(default_factory=list)
    opened: bool = False

    def open(self) -> None:
        # 记录生命周期调用，方便测试断言。
        self.opened = True
        self.commands.append("open")

    def close(self) -> None:
        self.commands.append("close")
        self.opened = False

    def enable_all(self) -> None:
        self.commands.append("enable_all")

    def disable_all(self) -> None:
        self.commands.append("disable_all")

    def control_vel(self, motor_id: int, velocity: float) -> None:
        self.velocities[motor_id] = velocity
        self.commands.append(f"vel:{motor_id}:{velocity:.6f}")

    def control_pos_vel(self, motor_id: int, position: float, velocity: float) -> None:
        self.positions[motor_id] = position
        self.velocities[motor_id] = velocity
        self.commands.append(f"pos_vel:{motor_id}:{position:.6f}:{velocity:.6f}")

    def get_position(self, motor_id: int) -> float:
        return self.positions.get(motor_id, 0.0)

    def get_velocity(self, motor_id: int) -> float:
        return self.velocities.get(motor_id, 0.0)

    def get_tau(self, motor_id: int) -> float:
        return self.torques.get(motor_id, 0.0)


class CxxMotorClient:
    # 对 C++ 桥接库做一层 ctypes 封装。
    def __init__(self, library_path: str, serial_number: str, nom_baud: int, dat_baud: int) -> None:
        self.library_path = Path(library_path)
        self.serial_number = serial_number
        self.nom_baud = nom_baud
        self.dat_baud = dat_baud
        self._lib: ctypes.CDLL | None = None
        self._handle: ctypes.c_void_p | None = None

    def open(self) -> None:
        # 延迟加载共享库，这样 mock 运行时不依赖本地原生组件。
        self._lib = ctypes.CDLL(str(self.library_path))
        self._bind_functions(self._lib)
        handle = self._lib.dm_bridge_open(
            self.serial_number.encode("utf-8"),
            ctypes.c_uint32(self.nom_baud),
            ctypes.c_uint32(self.dat_baud),
        )
        if not handle:
            raise RuntimeError(self._last_error())
        self._handle = ctypes.c_void_p(handle)

    def close(self) -> None:
        if self._lib is not None and self._handle is not None:
            self._lib.dm_bridge_close(self._handle)
        self._handle = None
        self._lib = None

    def enable_all(self) -> None:
        self._call("dm_bridge_enable_all")

    def disable_all(self) -> None:
        self._call("dm_bridge_disable_all")

    def control_vel(self, motor_id: int, velocity: float) -> None:
        self._call("dm_bridge_control_vel", ctypes.c_uint16(motor_id), ctypes.c_float(velocity))

    def control_pos_vel(self, motor_id: int, position: float, velocity: float) -> None:
        self._call(
            "dm_bridge_control_pos_vel",
            ctypes.c_uint16(motor_id),
            ctypes.c_float(position),
            ctypes.c_float(velocity),
        )

    def get_position(self, motor_id: int) -> float:
        return self._read_float("dm_bridge_get_position", motor_id)

    def get_velocity(self, motor_id: int) -> float:
        return self._read_float("dm_bridge_get_velocity", motor_id)

    def get_tau(self, motor_id: int) -> float:
        return self._read_float("dm_bridge_get_tau", motor_id)

    def _call(self, name: str, *args: object) -> None:
        if self._lib is None or self._handle is None:
            raise RuntimeError("motor client is not open")
        rc = getattr(self._lib, name)(self._handle, *args)
        if rc != 0:
            raise RuntimeError(self._last_error())

    def _read_float(self, name: str, motor_id: int) -> float:
        if self._lib is None or self._handle is None:
            raise RuntimeError("motor client is not open")
        value = ctypes.c_float()
        rc = getattr(self._lib, name)(self._handle, ctypes.c_uint16(motor_id), ctypes.byref(value))
        if rc != 0:
            raise RuntimeError(self._last_error())
        return float(value.value)

    def _last_error(self) -> str:
        if self._lib is None:
            return "C++ bridge library is not loaded"
        raw = self._lib.dm_bridge_last_error()
        return raw.decode("utf-8", errors="replace") if raw else "unknown bridge error"

    @staticmethod
    def _bind_functions(lib: ctypes.CDLL) -> None:
        lib.dm_bridge_open.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32]
        lib.dm_bridge_open.restype = ctypes.c_void_p
        lib.dm_bridge_close.argtypes = [ctypes.c_void_p]
        lib.dm_bridge_close.restype = None

        for name in ["dm_bridge_enable_all", "dm_bridge_disable_all"]:
            fn = getattr(lib, name)
            fn.argtypes = [ctypes.c_void_p]
            fn.restype = ctypes.c_int

        lib.dm_bridge_control_vel.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_float]
        lib.dm_bridge_control_vel.restype = ctypes.c_int
        lib.dm_bridge_control_pos_vel.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint16,
            ctypes.c_float,
            ctypes.c_float,
        ]
        lib.dm_bridge_control_pos_vel.restype = ctypes.c_int

        for name in ["dm_bridge_get_position", "dm_bridge_get_velocity", "dm_bridge_get_tau"]:
            fn = getattr(lib, name)
            fn.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.POINTER(ctypes.c_float)]
            fn.restype = ctypes.c_int

        lib.dm_bridge_last_error.argtypes = []
        lib.dm_bridge_last_error.restype = ctypes.c_char_p
