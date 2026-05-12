# 后端接口文档

这个项目目前没有独立的 Web 后端。
这里说的“后端接口”，指的是板子上 Python 控制程序对外暴露的稳定数据格式和启动入口。

当前最重要的接口有四类：

1. 主程序 CLI
2. 远程输入 UDP 协议
3. 遥测输出 JSONL / 控制台面板
4. 硬件校准报告

## 1. 主程序 CLI

入口：

```bash
python3 -m app.main [options]
```

常用参数：

- `--input gamepad|remote|hybrid|demo|neutral`
- `--mock`
- `--telemetry`
- `--plain-telemetry`
- `--log-file logs/run.jsonl`
- `--control-profile conservative|normal|sport`
- `--hardware-config configs/hardware.json`
- `--control-config configs/control.json`
- `--input-config configs/input.json`
- `--network-config configs/network.json`

输入模式含义：

- `gamepad`：只用板子本地手柄
- `remote`：只收远程输入
- `hybrid`：本地手柄和远程并存，远程新鲜时接管
- `demo`：脚本演示输入
- `neutral`：中位空闲输入

## 2. 远程输入 UDP 协议

远程端只发输入状态，不直接发电机命令。

传输格式：UDP + JSON。

字段定义：

- `seq`：包序号，`int`
- `timestamp`：发送时间戳，`float`
- `active`：是否启用当前输入，`bool`
- `left_x`：左摇杆 X，`float`
- `left_y`：左摇杆 Y，`float`
- `right_x`：右摇杆 X，`float`
- `right_y`：右摇杆 Y，`float`
- `mode_button`：模式切换键，`bool`
- `steering_lock_button`：转向锁键，`bool`
- `drive_direction_button`：前进/倒车切换键，`bool`
- `emergency_stop_button`：急停键，`bool`

前端或上位机只要会发这个 JSON，就能接入远程控制。

## 3. 遥测输出

遥测有两种出口：

### 3.1 控制台面板

启动 `--telemetry` 后会打印一页式状态面板，主要看：

- 当前模式
- 输入源
- 链路状态
- 远程序号
- 远程时延
- 急停状态
- 左右摇杆值
- 驱动轮/转向轮误差

### 3.2 JSONL 日志

加上：

```bash
--log-file logs/run.jsonl
```

就会把每一帧写成一行 JSON。

字段定义：

- `timestamp`
- `loop_index`
- `mode_name`
- `input_source`
- `input_link_state`
- `remote_seq`
- `remote_latency_s`
- `remote_stale`
- `steering_locked`
- `drive_direction_name`
- `emergency_stop`
- `driver_input`
- `drive_summary`
- `steer_summary`
- `drive_motors`
- `steer_motors`
- `notice`

### 3.3 `driver_input`

结构：

- `left_x`
- `left_y`
- `right_x`
- `right_y`
- `mode_button`
- `steering_lock_button`
- `drive_direction_button`
- `emergency_stop_button`

### 3.4 `drive_motors`

驱动轮结构化遥测数组。

每个元素字段：

- `role`：轮子角色名，例如 `front_left`
- `motor_id`：电机 ID
- `target`：目标值，单位 `rad/s`
- `actual`：实测值，单位 `rad/s`
- `error`：误差
- `unit`：单位字符串，通常是 `rad/s`

### 3.5 `steer_motors`

转向轮结构化遥测数组。

每个元素字段：

- `role`：轮子角色名，例如 `front_left`
- `motor_id`：电机 ID
- `target`：目标值，单位 `deg`
- `actual`：实测值，单位 `deg`
- `error`：误差
- `unit`：单位字符串，通常是 `deg`

### 3.6 `input_link_state` 建议值

目前代码会输出这些状态：

- `本地`
- `本地在线`
- `本地手柄`
- `本地急停`
- `远程空闲`
- `远程在线`
- `远程无效`
- `远程超时回退`
- `远程接管`

前端可以直接按这个字段做状态灯，不需要自己猜输入来源。

## 4. 硬件校准报告

入口：

```bash
python3 scripts/calibrate_hardware.py [options]
```

常用参数：

- `--verify`
- `--verify-steer-zero`
- `--calibrate-drive`
- `--calibrate-steer`
- `--set-steer-zero`
- `--save-flash`
- `--report-file logs/calibration.json`

报告字段大体包括：

- `hardware_config`
- `config_issues`
- `live_checks`
- `drive_direction_result`
- `calibrated_steer_ids`
- `steer_zero_checks`
- `result_inverted_drive_motor_ids`
- `save_flash`
- `notes`

这个报告适合前端做“校准结果页”。

## 5. HTTP 只读 API

程序可以通过下面的参数启动一个给前端用的只读接口：

```bash
python3 car_control_system.py --input hybrid --api --telemetry
```

默认地址：

- `http://127.0.0.1:8765`

常用接口：

- `GET /api/v1/health`
- `GET /api/v1/telemetry/latest`
- `GET /api/v1/telemetry/history?limit=100`
- `GET /api/v1/config/hardware`
- `GET /api/v1/config/control`
- `GET /api/v1/config/network`
- `GET /api/v1/calibration/latest`
- `GET /api/v1/meta`

返回格式统一是：

```json
{"ok": true, "data": {}}
```

当前遥测和元信息里都带 `schema_version`，默认是 `1`，前端可以用它判断字段是否兼容。

如果你是前端，优先接：

1. `/api/v1/health`
2. `/api/v1/telemetry/latest`
3. `/api/v1/telemetry/history`

这样就够做第一版仪表盘了。

## 6. 推荐的前端接法

当前最稳的接法不是直接控制电机，而是先做只读前端：

1. 读取 `logs/run.jsonl`
2. 读取 `logs/calibration.json`
3. 展示当前模式、链路、摇杆、轮子误差
4. 再加一个轻量 WebSocket 或 HTTP 只读接口

不建议一开始就让前端直接碰电机命令。

## 7. 兼容原则

- 板子永远是最终控制端
- 远程端只发输入状态
- `mode0 / mode1 / mode2` 是控制策略，不是输入来源
- `--input` 决定输入从哪来
- `B` 键决定当前控制模式

## 8. 前端最少需要的字段

如果只做一个最小仪表盘，先接这几个就够了：

- `mode_name`
- `input_source`
- `input_link_state`
- `remote_seq`
- `remote_latency_s`
- `steering_locked`
- `drive_direction_name`
- `emergency_stop`
- `driver_input`
- `drive_motors`
- `steer_motors`

这些字段已经足够判断：

- 是输入问题
- 是网络问题
- 是电机回显问题
- 还是控制逻辑问题
