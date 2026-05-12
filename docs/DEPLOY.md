# 部署流程

这个项目建议直接部署到 Ubuntu/ARM 板子上运行，不需要做交叉编译。

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

## ARM 板子快速流程

如果你现在就在 ARM 板子上，按这个顺序来：

1. 把整个项目目录拷到板子上
2. 进入项目根目录
3. 运行环境检查
4. 编译 C++ 桥接层
5. 先跑 mock 验证逻辑
6. 再跑 `mode2` 或低速档
7. 最后再上真机手柄和远程接管

推荐命令：

```bash
bash scripts/setup_board.sh
bash scripts/build_bridge.sh
python3 car_control_system.py --mock --input demo --max-loops 5 --telemetry
python3 car_control_system.py --input gamepad --control-profile conservative --telemetry
```

如果你只是想先看控制链路，不碰真车，先用：

```bash
bash scripts/run_mock.sh demo 5
```

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
- `--log-file path`：把遥测记录成 JSONL 文件

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

如果你要让车真正动起来，建议先校准这三项：

1. 驱动轮正反方向
2. 转向零点
3. 电机 ID 和角色映射

最常用的是这条：

```bash
python3 scripts/calibrate_hardware.py --all --save-flash
```

常用组合：

```bash
python3 scripts/calibrate_hardware.py --probe
python3 scripts/calibrate_hardware.py --verify
python3 scripts/calibrate_hardware.py --verify-steer-zero
python3 scripts/calibrate_hardware.py --calibrate-drive --write-config configs/hardware.local.json
python3 scripts/calibrate_hardware.py --calibrate-steer --save-flash
python3 scripts/calibrate_hardware.py --set-steer-zero --save-flash
python3 scripts/calibrate_hardware.py --all --save-flash --report-file logs/calibration.json
```

说明：

- `--verify` 会先检查 `hardware.json` 的配置自洽性，再检查电机在线响应
- `--verify-steer-zero` 会检查转向零点是否接近 0
- `--calibrate-drive` 会逐个点动驱动轮，让你确认正反
- `--calibrate-steer` 会把当前摆正位置写成零点
- `--set-steer-zero` 是独立的转向零点设置命令
- `--write-config` 只保存驱动反向列表，不会乱改电机 ID 映射
- `--save-flash` 会把零点保存到电机 flash
- `--report-file` 会把整次校准过程保存成 JSON 报告

## 让小车动起来的最短路径

如果你现在只想看到车动，不想先研究全部功能，按这个顺序：

1. 确认电源、CANFD、桥接板、转向机构都已接好
2. 运行：

```bash
bash scripts/setup_board.sh
bash scripts/build_bridge.sh
python3 scripts/calibrate_hardware.py --verify
python3 scripts/calibrate_hardware.py --verify-steer-zero
python3 car_control_system.py --input gamepad --control-profile conservative --telemetry
```

3. 先轻推左摇杆，看驱动轮是否往前
4. 再左右推左摇杆，看转向是否正确
5. 如果方向反了，先回到校准向导修正，不要直接改控制逻辑
6. 如果你要远程控制，再切到 `--input hybrid`

如果没有本地手柄，可以先用：

```bash
python3 car_control_system.py --mock --input demo --telemetry
```

这只能验证逻辑，不会让真车动。

## 给前端页面准备 API

如果你现在要开始写前端，板子上直接开只读接口：

```bash
python3 car_control_system.py --input hybrid --api --telemetry
```

默认地址是：

```text
http://127.0.0.1:8765
```

前端最先接这几个接口就够：

```text
/api/v1/health
/api/v1/telemetry/latest
/api/v1/telemetry/history?limit=100
```

后面再补：

```text
/api/v1/config/hardware
/api/v1/config/control
/api/v1/config/network
/api/v1/calibration/latest
```
