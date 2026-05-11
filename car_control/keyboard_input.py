from __future__ import annotations

from dataclasses import dataclass
import sys

from .types import DriverInput


@dataclass
class ScriptedInput:
    frames: list[DriverInput]
    index: int = 0

    def next(self) -> DriverInput:
        if not self.frames:
            return DriverInput()
        if self.index >= len(self.frames):
            return self.frames[-1]
        frame = self.frames[self.index]
        self.index += 1
        return frame


def neutral_input() -> DriverInput:
    return DriverInput()


def keyboard_stub() -> DriverInput:
    raise RuntimeError("keyboard input is not implemented yet; use scripted frames or joystick input later")
