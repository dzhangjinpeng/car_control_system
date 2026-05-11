# 部署流程

这个项目建议整包拷到 Ubuntu/ARM 板子上运行。

## 目录

拷贝整个目录即可：

```text
car_control_system/
```

## 板子准备

先跑环境检查：

```bash
bash scripts/setup_board.sh
```

如果要在板子上直接接手柄：

```bash
bash scripts/setup_board.sh --with-gamepad
```

它主要检查这些东西：

- `python3`
- `build-essential`
- `cmake`
- `pkg-config`
- `libusb-1.0-0-dev`
- `pygame`（只有手柄模式才需要）

## 编译桥接层

```bash
bash scripts/build_bridge.sh
```

这一步是把 Python 控制层和底层 C++ 桥接库连起来。

## 板子运行

本地手柄：

```bash
bash scripts/run_hardware.sh gamepad --telemetry
```

远程接收：

```bash
bash scripts/run_hardware.sh remote --telemetry
```

本地 + 远程并存：

```bash
bash scripts/run_hardware.sh hybrid --telemetry
```

## 一键部署

```bash
bash scripts/deploy.sh --run --input hybrid --telemetry
```

常用参数：

- `--no-build`：跳过桥接层编译
- `--run`：部署后直接启动
- `--mock`：不用真实硬件
- `--input demo|neutral|gamepad|remote|hybrid`
- `--control-profile conservative|normal|sport`
- `--max-loops N`
- `--telemetry`

示例：

```bash
bash scripts/deploy.sh --run --input gamepad --telemetry
```

```bash
bash scripts/deploy.sh --run --mock --input demo --max-loops 5
```

## Windows 推送到板子

```powershell
.\scripts\deploy.ps1 -Host 192.168.1.50 -User ubuntu -RemoteRoot /opt/car-control
```

常用参数：

- `-SkipBridgeBuild`：跳过板子上的桥接层编译
- `-SmokeTest`：部署后跑一个短的 mock 验证
- `-RemotePython`：板子上的 Python 命令名
- `-ControlProfile`：选择控制档位

## 脚本职责

- `scripts/setup_board.sh`：检查和补依赖
- `scripts/build_bridge.sh`：编译桥接层
- `scripts/run_mock.sh`：本地逻辑验证
- `scripts/run_hardware.sh`：板子真机运行
- `scripts/deploy.sh`：板子上一键部署
- `scripts/deploy.ps1`：Windows 远程部署
- `scripts/calibrate_hardware.py`：硬件校准向导，检查电机回显、校准驱动方向、写转向零点

## 硬件校准向导

先做一次安全校准，特别是新车、改线、换电机后。

```bash
python3 scripts/calibrate_hardware.py --all --save-flash
```

常用组合：

```bash
python3 scripts/calibrate_hardware.py --probe
python3 scripts/calibrate_hardware.py --verify
python3 scripts/calibrate_hardware.py --calibrate-drive --write-config configs/hardware.local.json
python3 scripts/calibrate_hardware.py --calibrate-steer --save-flash
```

说明：

- `--verify` 会先检查 `hardware.json` 的配置自洽性，再检查电机在线响应
- `--calibrate-drive` 会逐个点动驱动轮，让你确认正反
- `--calibrate-steer` 会把当前摆正位置写成零点
- `--write-config` 只保存驱动反向列表，不会乱改电机 ID 映射
- `--save-flash` 会把零点保存到电机 flash
