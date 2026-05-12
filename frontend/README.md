# 小车控制诊断前端

这个前端用于查看板端后端暴露的只读诊断数据，当前不直接下发电机控制命令。真实控制仍然由板子上的 Python 控制主程序负责。

## 本地启动

前端需要 Node.js 20 或更高版本。开发板上如果 Node.js 太旧，先在项目根目录运行：

```bash
chmod +x scripts/setup_frontend_node.sh
./scripts/setup_frontend_node.sh
```

先启动后端：

```bash
python3 car_control_system.py --input hybrid --api --telemetry --api-host 0.0.0.0
```

再启动前端：

```bash
npm install
npm run dev
```

Vite 开发服务器会把 `/api` 代理到 `http://127.0.0.1:8765`。如果前端和后端不在同一台机器，可以设置：

```bash
VITE_API_BASE=http://板子IP:8765/api/v1 npm run dev
```

## 页面

- `总览`：查看当前模式、输入源、远程链路、手柄输入、电机目标和回显误差。
- `配置`：查看车身尺寸、电机 ID 映射、控制参数和远程输入端口。
- `校准`：查看最近一次硬件校准报告。
- `历史`：查看最近遥测帧，并按模式、输入源、链路状态筛选。

## 数据模式

右上角可以切换：

- `模拟数据`：前端本地假数据，不需要后端，适合调页面。
- `真实后端`：请求后端 `/api/v1` 接口，适合板端或局域网调试。
