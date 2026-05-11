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

## 你现场先这么跑

1. 先确认板子和电脑在同一局域网
2. 在板子上启动 `--input hybrid`
3. 在电脑上启动 `remote_control_sender.py`
4. 先试前进、后退、转向
5. 再试断开电脑发送，看板子是否回到本地手柄

