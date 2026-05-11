# 使用流程

这个项目现在按“板子负责最终控车，电脑只发输入状态”的方式工作。

## 一次看懂的流程

1. 把 `car_control_system/` 拷到板子上
2. 在板子上跑环境检查
3. 编译桥接层
4. 先用 mock 验证控制逻辑
5. 再切到本地手柄真机
6. 如果要远程，再同时启动板子端和电脑端

## 板子本地测试

先检查环境：

```bash
bash scripts/setup_board.sh
```

如果板子要直连手柄，再加：

```bash
bash scripts/setup_board.sh --with-gamepad
```

编译桥接层：

```bash
bash scripts/build_bridge.sh
```

纯软件验证：

```bash
bash scripts/run_mock.sh demo 5
```

板子真机本地手柄：

```bash
bash scripts/run_hardware.sh gamepad --telemetry
```

## 远程控制流程

板子端开接收：

```bash
python3 car_control_system.py --input remote --telemetry
```

或者本地手柄和远程并存：

```bash
python3 car_control_system.py --input hybrid --telemetry
```

电脑端开发送：

```powershell
python remote_control_sender.py --host 192.168.1.50 --input gamepad
```

## 模式怎么切

这里要分两层看。

### 1. 控制模式切换

这是车的控制算法模式，靠手柄 `B` 键切换：

- `mode0`
- `mode1`
- `mode2`

### 2. 本地 / 远程切换

这是输入来源，靠启动参数选：

- `--input gamepad`：只用本地手柄
- `--input remote`：只收远程输入
- `--input hybrid`：本地和远程都开，远程新鲜时接管，断线自动回本地

所以你不是在运行中手动“切本地/远程”，而是启动时选好输入源。

## 常用命令对照

- `scripts/run_mock.sh demo 5`：看逻辑，不碰硬件
- `scripts/run_hardware.sh gamepad --telemetry`：板子本地手柄真机
- `python3 car_control_system.py --input hybrid --telemetry`：板子本地 + 远程
- `python remote_control_sender.py --host <板子IP> --input gamepad`：电脑发手柄

## 手柄自动匹配

`configs/input.json` 默认开启：

```json
"auto_detect": true
```

程序会根据手柄名称自动匹配常见布局：

- Xbox / XInput 手柄
- PlayStation DualShock / DualSense 手柄
- 常见 SDL 通用手柄

查看系统识别到的手柄：

```bash
python3 car_control_system.py --list-gamepads
```

电脑端远程发送器也可以查看：

```powershell
python remote_control_sender.py --list-gamepads
```

如果自动匹配不准，把 `auto_detect` 改成 `false`，再手动修改 `left_x_axis`、`right_x_axis` 和按键编号。

## 你现场先这么跑

1. 先确认板子和电脑在同一局域网
2. 在板子上启动 `--input hybrid`
3. 在电脑上启动 `remote_control_sender.py`
4. 先试前进、后退、转向
5. 再试断开电脑发送，看板子是否回到本地手柄

## 更好看的日志

如果你在终端里直接跑，默认会显示刷新式状态面板，而不是一长串单行日志。

你还可以把每一帧记录到文件：

```bash
python3 car_control_system.py --input hybrid --telemetry --log-file logs/run.jsonl
```

如果你想强制用单行文本：

```bash
python3 car_control_system.py --input hybrid --telemetry --plain-telemetry
```

## 硬件校准

如果你怀疑电机方向、零点或者角色映射有问题，先跑：

```bash
python3 scripts/calibrate_hardware.py --all --save-flash
```

它会：

- 打印每个电机的实时回显
- 先检查配置是否自洽，再检查电机是否在线响应
- 可以单独验证转向零点：

```bash
python3 scripts/calibrate_hardware.py --verify-steer-zero
```
- 点动驱动轮，让你确认正反
- 把转向轮当前摆正位置写成零点
- 需要的话还能写出 `configs/hardware.local.json`

这比直接改控制逻辑更稳。

如果你只想先验一遍，不做任何改写，跑：

```bash
python3 scripts/calibrate_hardware.py --verify
```
