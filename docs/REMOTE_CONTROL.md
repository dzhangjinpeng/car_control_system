# 远程控制

## 原则

- 板子始终负责最终控车
- 电脑端只发送输入状态
- 本地手柄始终保留，作为默认控制和安全回退

## 结构

```text
本地手柄 -> 板子 Python 控制程序 -> 电机
远程手柄 -> 电脑发送器 -> UDP -> 板子 Python 控制程序 -> 电机
```

## 三种启动方式

### 本地模式

只用板子本地手柄：

```bash
python3 car_control_system.py --input gamepad --telemetry
```

适合现场直连测试。

### 远程模式

板子只收远程输入：

```bash
python3 car_control_system.py --input remote --telemetry
```

适合板子在车上、你在另一台电脑上操作。

### 混合模式

板子同时保留本地手柄和远程输入：

```bash
python3 car_control_system.py --input hybrid --telemetry
```

规则是：

- 本地急停永远优先
- 远程包新鲜时接管
- 远程断线后自动回本地

## 电脑端发送器

电脑上运行：

```powershell
python remote_control_sender.py --host 192.168.1.50 --input gamepad
```

它只负责把本机手柄状态发给板子，不直接碰电机。

## 要不要公网 IP

不一定。

- 同一局域网测试，不需要公网 IP
- 跨网络控制，才需要公网可达或 VPN / 内网穿透

## 端口和配置

默认配置在 `configs/network.json`：

- `bind_host = 0.0.0.0`
- `port = 23333`
- `timeout_s = 0.2`

板子只要能收到这个 UDP 端口的数据就行。

## 传输步骤

1. 先确认板子 IP
2. 在板子上启动 `remote` 或 `hybrid`
3. 在电脑上启动发送器
4. 先试低速前进、后退、转向
5. 断开电脑发送，确认板子能回到本地手柄

## 输入切换和模式切换的区别

这是两个概念。

### 输入切换

指的是本地 / 远程 / 混合，靠启动参数选。

### 控制模式切换

指的是 `mode0 / mode1 / mode2`，靠手柄 `B` 键切。

所以：

- `--input` 决定输入从哪来
- `B` 键决定车怎么开

