from __future__ import annotations

import math

def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def deg_to_rad(value: float) -> float:
    return value * math.pi / 180.0


def rad_to_deg(value: float) -> float:
    return value * 180.0 / math.pi
