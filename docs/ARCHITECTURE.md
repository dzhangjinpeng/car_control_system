# 项目流程图

```mermaid
flowchart TD
    A[启动项目] --> B{选择输入源}
    B -->|gamepad| C[板子本地手柄]
    B -->|remote| D[板子接收 UDP 远程输入]
    B -->|hybrid| E[本地手柄 + 远程输入并存]
    B -->|demo/neutral| F[脚本输入或空闲输入]

    C --> G[输入标准化 / 自动匹配手柄]
    D --> H[远程包解析 / 超时判断]
    E --> I[本地优先 + 远程接管 + 本地急停优先]
    F --> J[脚本帧输出]

    G --> K[CarController]
    H --> K
    I --> K
    J --> K

    K --> L{控制模式}
    L -->|mode0| M[兼容原地旋转]
    L -->|mode1| N[前轮 Ackermann 转向]
    L -->|mode2| O[低速安全调试]

    M --> P[速度 / 转向目标]
    N --> P
    O --> P

    P --> Q[安全层]
    Q --> R[驱动轮速度斜坡]
    Q --> S[急停 / 失能 / 回中]

    R --> T[C++ 桥接层]
    S --> T
    T --> U[libu2canfd.a / 达妙电机]

    U --> V[驱动轮 / 转向轮实际动作]
```

## 校准流程

```text
硬件连通 -> scripts/calibrate_hardware.py --verify
          -> scripts/calibrate_hardware.py --calibrate-drive
          -> scripts/calibrate_hardware.py --calibrate-steer --save-flash
          -> 保存 configs/hardware.local.json
          -> 真机验证
```

## 现在还值得继续优化的点

1. 自动生成更完整的现场报告
   - 把 `--verify` 的结果输出成一份可保存的校准报告

2. 驱动方向确认再自动化一点
   - 现在已经能点动和记录，但“正向是否推车前进”仍要人工看

3. 零点校准做成独立命令
   - 现在在向导里能做，后面可以单独拆成 `--set-zero`

4. 远程输入加确认机制
   - 可以考虑增加可选 ACK / 心跳摘要，方便看丢包和延迟

5. 现场调参文件分层
   - 把“固定硬件参数”和“现场临时参数”彻底分开，减少误改

6. 真机诊断回显再细一点
   - 增加每个轮子的目标值、实测值、误差值

7. 车身尺寸自检
   - 轴距、轮距、减速比合法性已经能查，还可以加范围提示

