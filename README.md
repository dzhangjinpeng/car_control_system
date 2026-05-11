# Car Control System

这是小车控制项目的主工作区。

## 先看这几个文档

- [快速流程](docs/USAGE.md)
- [部署流程](docs/DEPLOY.md)
- [远程控制](docs/REMOTE_CONTROL.md)
- [调参表](docs/TUNING.md)

## 主入口

```text
car_control_system.py
```

## 常用脚本

- `scripts/setup_board.sh`：板子环境检查和依赖安装
- `scripts/build_bridge.sh`：编译 C++ 桥接层
- `scripts/run_mock.sh`：纯软件模拟
- `scripts/run_hardware.sh`：板子真机运行
- `scripts/deploy.sh`：板子上一键安装、编译、运行
- `scripts/deploy.ps1`：Windows 端远程部署到板子
- `remote_control_sender.py`：电脑端把手柄输入发给板子
