# 后端接口说明

这个项目当前没有单独的 Web 后端。
现在能给前端对接的，主要是三类稳定接口：

1. 控制入口参数
2. 遥测输出
3. 校准报告

前端如果要接，建议先做只读诊断面板，不要直接替代控制链路。

## 1. 控制入口

主程序：

```bash
python3 car_control_system.py [options]
```

常用参数：

- `--input gamepad|remote|hybrid|demo|neutral`
- `--telemetry`
- `--plain-telemetry`
- `--log-file logs/run.jsonl`
- `--mock`
- `--control-profile conservative|normal|sport`

硬件校准入口：

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

## 2. 遥测输出

### 控制台面板

`--telemetry` 默认会输出一页式状态面板，包含：

- 当前模式
- 输入来源
- 转向锁
- 方向锁
- 急停状态
- 左右摇杆
- 驱动轮摘要
- 转向轮摘要

### JSONL 日志

如果加了：

```bash
--log-file logs/run.jsonl
```

会写出一行一个 JSON 的日志文件。

每一帧的字段：

- `timestamp`
- `loop_index`
- `mode_name`
- `input_source`
- `steering_locked`
- `drive_direction_name`
- `emergency_stop`
- `driver_input`
- `drive_summary`
- `steer_summary`
- `notice`

### 建议前端展示

前端最好分成这些区域：

- 顶部总状态条：模式、输入源、急停、连接状态
- 中部控制面板：左右摇杆、方向锁、转向锁
- 底部电机表格：每个电机的目标、实测、误差
- 右侧日志流：最新事件和报警

## 3. 校准报告

如果加了：

```bash
--report-file logs/calibration.json
```

会输出一份结构化校准报告，字段大致包括：

- `hardware_config`
- `config_issues`
- `live_checks`
- `drive_direction_result`
- `calibrated_steer_ids`
- `steer_zero_checks`
- `result_inverted_drive_motor_ids`
- `save_flash`
- `notes`

这个文件适合给前端做“校准结果页”。

## 4. 远程输入包

电脑端发送器发的是 UDP JSON 包，不是电机命令。

字段：

- `seq`
- `timestamp`
- `active`
- `left_x`
- `left_y`
- `right_x`
- `right_y`
- `mode_button`
- `steering_lock_button`
- `drive_direction_button`
- `emergency_stop_button`

## 5. 前端接入建议

如果你要让前端同学接这个项目，最实用的方案是：

1. 先做一个只读仪表盘
2. 仪表盘读 JSONL 遥测和校准报告
3. 再补一个轻量 WebSocket/HTTP 接口
4. 最后才考虑把“启动校准”和“切模式”做成按钮

### 不建议一开始就做的事

- 让前端直接下电机命令
- 让前端跳过 `CarController`
- 让前端同时承担控制和调试

这样很容易把问题定位搞乱。

## 6. 最小可用接口

如果只做一个最小前端，建议先支持这三个文件：

- `logs/run.jsonl`
- `logs/calibration.json`
- `configs/hardware.json`

只要前端能读这三个文件，就已经能看出大部分硬件和逻辑问题。
