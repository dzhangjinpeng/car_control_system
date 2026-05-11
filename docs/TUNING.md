# 调参表

## 参数挡位

| 挡位 | 适合场景 | 特点 |
| --- | --- | --- |
| `conservative` | 初次上车、低速验车 | 更稳、更慢、转向更柔和 |
| `normal` | 默认日常调试 | 速度和响应比较均衡 |
| `sport` | 熟悉车况后追求响应 | 更快、更直接、更容易冲 |

运行时可直接选：

```powershell
python car_control_system.py --mock --input demo --control-profile normal
```

## 主要参数含义

| 参数 | 调大后 | 调小后 |
| --- | --- | --- |
| `max_linear_speed` | 最高速度更快 | 最高速度更慢 |
| `throttle_smoothing_alpha` | 油门响应更快 | 油门更平顺 |
| `steering_smoothing_alpha` | 转向响应更快 | 转向更平顺 |
| `throttle_curve_power` | 小幅推杆更不敏感 | 小幅推杆更敏感 |
| `steering_curve_power` | 小角度转向更直接 | 小角度转向更细腻 |
| `drive_speed_ramp_mps_per_s` | 加减速更快 | 加减速更柔和 |
| `mode1.max_inner_steering_degrees` | 转弯半径更小 | 转弯更缓 |
| `mode1.turn_speed_min_scale` | 转弯时最低速度更低 | 转弯时速度保留更多 |
| `mode1.turn_speed_curve_power` | 大转角时降速更明显 | 大转角时降速更平缓 |
| `mode2.speed_scale` | 调试模式更快 | 调试模式更慢 |

## 建议顺序

1. 先选挡位
2. 再改 `max_linear_speed`
3. 再改 `drive_speed_ramp_mps_per_s`
4. 最后调转向曲线和转弯降速

## 当前急停键

当前默认把 `BACK` 当作紧急停车键。  
如果你公司那只手柄按键编号不同，只改 `configs/input.json` 里的 `emergency_stop_button`。

## 方向锁

当前默认把 `RB` 当作方向锁切换键。  
它不会切换 `mode0/mode1/mode2`，只限制前后速度方向：

- `自动`：摇杆向上前进，向下倒车
- `只前进`：不管摇杆 Y 正负，输出都按前进方向
- `只倒车`：不管摇杆 Y 正负，输出都按倒车方向

如果公司手柄按键编号不同，只改 `configs/input.json` 里的 `drive_direction_button`。
