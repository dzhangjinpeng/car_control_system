from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DriveSpeedRamping:
    # 记录每个轮子的当前线速度目标，避免命令一下跳太多。
    current_linear_speeds: dict[str, float] = field(default_factory=dict)

    def reset(self) -> None:
        # 切模式时清空缓存，让新模式从零开始再爬升。
        self.current_linear_speeds.clear()

    def apply(self, targets: dict[str, float], max_delta: float) -> dict[str, float]:
        # 每一轮只允许速度变化一小步，形成斜坡。
        max_delta = max(0.0, max_delta)
        shaped: dict[str, float] = {}
        for role, target in targets.items():
            current = self.current_linear_speeds.get(role, 0.0)
            delta = target - current
            if delta > max_delta:
                current += max_delta
            elif delta < -max_delta:
                current -= max_delta
            else:
                current = target
            self.current_linear_speeds[role] = current
            shaped[role] = current
        return shaped
