# 前端 API

这个项目现在提供一个只读 HTTP 接口，专门给前端页面用。

## 启动方式

```bash
python3 car_control_system.py --input hybrid --api --telemetry
```

默认监听：

- `127.0.0.1:8765`

你也可以改成局域网可访问：

```bash
python3 car_control_system.py --input hybrid --api --api-host 0.0.0.0 --api-port 8765 --telemetry
```

## CORS

接口已开放基础 CORS：

- `Access-Control-Allow-Origin: *`

所以前端开发时可以直接从浏览器请求，不必先做代理。

## 通用返回格式

所有接口都返回同样的包裹结构：

```json
{
  "ok": true,
  "data": {}
}
```

错误时：

```json
{
  "ok": false,
  "error": "message"
}
```

## 接口列表

### 1. 健康检查

```http
GET /api/v1/health
```

返回：

- `telemetry_ready`
- `latest_loop_index`
- `mode_name`
- `input_source`
- `input_link_state`
- `schema_version`
- `startup_checks`
- `config_issues`

其中 `startup_checks.ok` 表示当前环境是否已经准备好真机运行，例如桥接库是否已编译、配置是否自洽。

### 2. 最新遥测

```http
GET /api/v1/telemetry/latest
```

返回一帧完整遥测，字段和 JSONL 一致。

### 3. 遥测历史

```http
GET /api/v1/telemetry/history?limit=100
```

参数：

- `limit`：默认 100，最大 500

### 4. 硬件配置

```http
GET /api/v1/config/hardware
```

用于前端展示电机 ID、轮子参数、驱动/转向角色映射。

### 5. 控制配置

```http
GET /api/v1/config/control
```

用于前端展示当前调参挡位和关键控制参数。

### 6. 网络配置

```http
GET /api/v1/config/network
```

用于前端显示远程输入监听端口和超时时间。

### 7. 校准报告

```http
GET /api/v1/calibration/latest
```

默认读取：

```text
logs/calibration.json
```

如果文件不存在，返回 `null`。

### 8. 元信息

```http
GET /api/v1/meta
```

返回服务名、版本和可用接口列表。

其中也会带上 `schema_version`，前端可以据此判断字段是否兼容。

## 前端建议接法

先接这三个就够了：

1. `/api/v1/health`
2. `/api/v1/telemetry/latest`
3. `/api/v1/telemetry/history`

后面再补：

- `/api/v1/config/hardware`
- `/api/v1/config/control`
- `/api/v1/calibration/latest`

## 页面建议

前端第一版建议分成三块：

- 总览页：模式、输入源、链路状态、摇杆、电机误差
- 校准页：校准报告、驱动方向、转向零点
- 历史页：最近遥测表格和筛选器

这三块已经足够把现场问题定位出来。
