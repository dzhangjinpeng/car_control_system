# 现场常用命令

这份文件专门用于公司电脑或开发板现场复制命令。  
以后我更新命令后，你只需要在公司电脑或开发板执行 `git pull`。

## 1. 第一次下载项目

```bash
git clone https://github.com/dzhangjinpeng/car_control_system.git
cd car_control_system
```

## 2. 更新最新代码

```bash
cd car_control_system
git pull
```

如果你已经在开发板的 `~/car_control_system` 目录：

```bash
cd ~/car_control_system
git pull
```

## 3. Ubuntu 开发板安装环境

```bash
chmod +x scripts/*.sh
./scripts/setup_board.sh --with-gamepad
```

## 4. 编译 C++ 桥接层

```bash
./scripts/build_bridge.sh
```

## 5. 查看系统识别到的手柄

```bash
python3 car_control_system.py --list-gamepads
```

## 6. 查看手柄原始轴和按键编号

```bash
python3 scripts/inspect_gamepad.py
```

操作方法：

- 一次只动一个摇杆或按一个键。
- 看哪个 `axis` 或 `button` 变化。
- 如果右摇杆一直是 `-1`，通常是 `right_x_axis` 读到了扳机轴。

## 7. 修改手柄映射

```bash
nano configs/input.json
```

配置文件里以下划线开头的字段是中文说明，例如 `_right_x_axis`。  
这些说明字段不会影响程序运行，可以保留。

如果自动匹配覆盖了你的手动配置，把：

```json
"auto_detect": true
```

改成：

```json
"auto_detect": false
```

常见要改的字段：

```json
"auto_detect": false,
"left_x_axis": 0,
"left_y_axis": 1,
"right_x_axis": 3,
"right_y_axis": 4
```

具体数字以 `scripts/inspect_gamepad.py` 实测为准。

## 8. 纯软件模拟

不碰硬件，不会让车动：

```bash
python3 car_control_system.py --mock --input neutral --telemetry
```

自动模拟输入：

```bash
python3 car_control_system.py --mock --input demo --telemetry
```

## 9. 用 mock 测手柄

不碰真实电机，只看手柄输入是否正确：

```bash
python3 car_control_system.py --mock --input gamepad --gamepad-index 0 --telemetry
```

## 10. 硬件检查

确认 CANFD、电机供电、急停和安全支架都准备好后再跑：

```bash
python3 scripts/calibrate_hardware.py --verify --verify-steer-zero --report-file logs/calibration.json
```

## 11. 真机本地手柄控制

第一次建议架空轮子，低速小幅推动摇杆：

```bash
python3 car_control_system.py --input gamepad --telemetry
```

## 12. 真机控制 + 后端 API

如果要让前端页面看状态：

```bash
python3 car_control_system.py --input hybrid --api --telemetry --api-host 0.0.0.0
```

后端健康检查地址：

```text
http://开发板IP:8765/api/v1/health
```

## 13. 公司电脑启动前端

```bash
cd frontend
npm install
```

Windows PowerShell：

```powershell
$env:VITE_API_BASE="http://开发板IP:8765/api/v1"
npm run dev -- --host 0.0.0.0 --port 5173
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

前端右上角切到 `真实后端`。

## 14. 开发板升级 Node.js

如果开发板上 `npm run dev` 报 `Unexpected token '.'` 这类语法错误，先升级 Node.js：

```bash
chmod +x scripts/setup_frontend_node.sh
./scripts/setup_frontend_node.sh
```

升级完再进入前端目录：

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## 15. 出问题时先复制这些输出

```bash
git status
git log --oneline -5
python3 car_control_system.py --list-gamepads
python3 scripts/inspect_gamepad.py
```

硬件相关问题再复制：

```bash
python3 scripts/calibrate_hardware.py --verify --verify-steer-zero --report-file logs/calibration.json
```
