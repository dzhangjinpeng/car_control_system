# ARM 开发板现场部署与实测流程

这份文档用于下午或明天去公司现场调车时照着执行。当前项目包名：

```text
car_control_system_release.zip
```

推荐分工：

- ARM Ubuntu 开发板：运行小车控制程序、C++ 桥接层、CANFD、电机通信、后端 API。
- 你的电脑：运行前端诊断页面，用浏览器查看状态。

## 1. 把项目传到 ARM 开发板

在电脑上执行：

```bash
scp car_control_system_release.zip 用户名@板子IP:/home/用户名/
```

如果不用 `scp`，也可以直接用 U 盘/硬盘把压缩包拷到开发板。

## 2. 在开发板上解压

```bash
cd /home/用户名
unzip car_control_system_release.zip
cd car_control_system
```

## 3. 安装环境

```bash
chmod +x scripts/*.sh
./scripts/setup_board.sh
```

这个脚本主要检查和安装：

- Python 环境
- 编译工具
- 项目运行依赖
- Linux 设备权限相关配置

## 4. 编译 C++ 硬件桥接层

```bash
./scripts/build_bridge.sh
```

注意：

- `libu2canfd.a` 仍然是必须保留的底层库。
- Python 不直接重写这个底层库，而是通过 C++ 桥接层调用它。
- 如果这里编译失败，先不要跑真车，需要先解决编译或架构问题。

## 5. 先跑纯模拟

不接硬件时先执行：

```bash
python3 car_control_system.py --mock --input neutral --telemetry
```

能看到中文遥测面板，说明 Python 主程序、配置读取、控制循环本身是能跑的。

## 6. 连接硬件后做检查

接好 CANFD、上电机、确认急停安全后，先跑：

```bash
python3 scripts/calibrate_hardware.py --verify --verify-steer-zero --report-file logs/calibration.json
```

重点看：

- CANFD 是否能通信
- 驱动电机 ID 是否匹配
- 转向电机 ID 是否匹配
- 转向零点是否合理
- 是否有明显配置问题

如果报告里有问题，先不要让车动。

## 7. 启动真机控制和后端 API

```bash
python3 car_control_system.py --input hybrid --api --telemetry --api-host 0.0.0.0
```

含义：

- `--input hybrid`：本地手柄和远程输入都支持，远程输入新鲜时可接管。
- `--api`：启动给前端看的只读后端接口。
- `--telemetry`：控制台显示中文状态面板。
- `--api-host 0.0.0.0`：允许局域网电脑访问开发板 API。

默认后端地址：

```text
http://板子IP:8765/api/v1
```

可以先在电脑浏览器打开：

```text
http://板子IP:8765/api/v1/health
```

如果能看到 JSON，说明前端可以接这个后端。

## 8. 在电脑上启动前端

电脑进入前端目录：

```bash
cd car_control_system/frontend
npm install
```

Linux/macOS 写法：

```bash
VITE_API_BASE=http://板子IP:8765/api/v1 npm run dev -- --host 0.0.0.0 --port 5173
```

Windows PowerShell 写法：

```powershell
$env:VITE_API_BASE="http://板子IP:8765/api/v1"
npm run dev -- --host 0.0.0.0 --port 5173
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

前端右上角切换：

- `模拟数据`：只看前端假数据。
- `真实后端`：读取 ARM 开发板后端 API。

## 9. 现场必须确认的硬件项

这些不能只靠离线代码百分百确认，必须现场看回显：

1. CANFD 通讯是否正常。
2. 电机 ID 是否和 `configs/hardware.json` 一致。
3. 驱动电机方向是否正确。
4. 转向电机零点是否正确。
5. 手柄按键编号是否正确。
6. 急停按钮是否能立刻让目标速度归零。
7. 前进、后退、左转、右转是否和前端/控制台显示一致。

## 10. 推荐实测顺序

1. 先跑 `--mock --input neutral`，确认程序能启动。
2. 跑 `calibrate_hardware.py --verify`，确认通信和 ID。
3. 不架空车轮前，不要直接给大速度。
4. 先用保守挡位或低速参数。
5. 手柄小幅推动，观察前端：
   - 输入摇杆是否变化
   - 驱动目标是否变化
   - 转向目标是否变化
   - 电机 actual 是否跟随 target
6. 如果方向反了，先停机，再改配置或校准结果。
7. 如果转向角不对，先处理转向零点和车身尺寸参数。

## 11. 运动学参数后续要调什么

主要看配置文件：

```text
configs/hardware.json
configs/control.json
```

需要现场确认或测量：

- 轴距：前后轮中心距离。
- 轮距：左右轮中心距离。
- 轮半径。
- 最大安全速度。
- 最大转向角。
- 左右电机方向是否需要取反。
- 转向零点偏移。

如果这些参数不准，现象通常是：

- 转弯半径不对。
- 左右轮速度比例不对。
- 前轮角度看起来不协调。
- 明明摇杆居中，车轮还有偏角。

## 12. 常用命令汇总

纯模拟：

```bash
python3 car_control_system.py --mock --input neutral --telemetry
```

本地手柄：

```bash
python3 car_control_system.py --input gamepad --telemetry
```

本地加远程：

```bash
python3 car_control_system.py --input hybrid --api --telemetry --api-host 0.0.0.0
```

硬件检查：

```bash
python3 scripts/calibrate_hardware.py --verify --verify-steer-zero --report-file logs/calibration.json
```

前端：

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## 13. 当前项目状态

当前软件侧已经具备：

- Python 控制主程序
- C++ 硬件桥接层
- 保留官方/底层 `libu2canfd.a`
- 本地手柄输入
- 远程 UDP 输入
- hybrid 本地/远程混合输入
- mode0 / mode1 / mode2 控制模式
- mock 模拟模式
- 中文控制台遥测
- JSONL 日志
- 硬件校准脚本
- 只读 HTTP 后端 API
- React 前端诊断页面

现场重点不是继续大改代码，而是先把硬件链路、电机方向、转向零点和手柄映射确认清楚。
