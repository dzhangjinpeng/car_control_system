from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriverInput:
    left_x: float = 0.0
    left_y: float = 0.0
    right_x: float = 0.0
    right_y: float = 0.0
    mode_button: bool = False
    steering_lock_button: bool = False
    drive_direction_button: bool = False
    emergency_stop_button: bool = False


@dataclass(frozen=True)
class StickState:
    angle_deg: float
    magnitude: float
