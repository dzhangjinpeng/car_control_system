import { useEffect, useMemo, useState } from 'react';
import { api } from '../apiClient';
import type { ControlConfig, HardwareConfig, NetworkConfig } from '../types';

interface ConfigState {
  hardware: HardwareConfig | null;
  control: ControlConfig | null;
  network: NetworkConfig | null;
}

function formatArray(values: number[]) {
  return values.join(', ');
}

function formatRoleMap(values: Record<string, number>) {
  return Object.entries(values)
    .map(([role, motorId]) => `${role}=${motorId}`)
    .join('  ');
}

function ConfigCheck() {
  const [config, setConfig] = useState<ConfigState>({ hardware: null, control: null, network: null });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchConfig = async () => {
      // 三个配置接口都是只读接口，只用于现场核对参数。
      const [hardware, control, network] = await Promise.all([
        api.getHardwareConfig(),
        api.getControlConfig(),
        api.getNetworkConfig(),
      ]);
      if (!mounted) {
        return;
      }

      const failed = [hardware, control, network].find((item) => !item.ok);
      if (failed) {
        setError(failed.error || '读取配置失败');
        return;
      }

      setConfig({
        hardware: hardware.data || null,
        control: control.data || null,
        network: network.data || null,
      });
      setError(null);
    };

    fetchConfig();
    return () => {
      mounted = false;
    };
  }, []);

  const warnings = useMemo(() => {
    const result: string[] = [];
    if (config.hardware && config.hardware.wheelbase <= config.hardware.track_width) {
      result.push('轴距小于或等于轮距，请确认车身尺寸是否填反。');
    }
    if (config.hardware && config.hardware.inverted_drive_motor_ids.length === 0) {
      result.push('没有配置反向驱动电机，若真车左右轮方向相反，需要检查该项。');
    }
    if (config.control && config.control.max_linear_speed > 0.7) {
      result.push('最大线速度偏高，初次真车建议先使用 conservative 或 normal。');
    }
    return result;
  }, [config]);

  if (error) {
    return <div className="alert danger">加载错误：{error}</div>;
  }

  if (!config.hardware || !config.control || !config.network) {
    return <div className="loading">等待配置数据...</div>;
  }

  return (
    <div className="stack">
      <section className="panel">
        <div className="panel-heading">
          <h2>配置检查</h2>
          <span>只读显示，不会修改小车参数</span>
        </div>
        {warnings.length > 0 ? (
          <ul className="issue-list">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : (
          <p className="empty-text">基础配置未发现明显风险。</p>
        )}
      </section>

      <section className="panel">
        <h2>车身与 CANFD</h2>
        <div className="summary-grid">
          <div><span>轴距</span><strong>{config.hardware.wheelbase} m</strong></div>
          <div><span>轮距</span><strong>{config.hardware.track_width} m</strong></div>
          <div><span>轮半径</span><strong>{config.hardware.wheel_radius} m</strong></div>
          <div><span>减速比</span><strong>{config.hardware.gear_ratio}</strong></div>
          <div><span>标称波特率</span><strong>{config.hardware.nom_baud}</strong></div>
          <div><span>数据波特率</span><strong>{config.hardware.dat_baud}</strong></div>
        </div>
        <div className="kv-list">
          <div><span>设备序列号</span><strong>{config.hardware.serial_number}</strong></div>
          <div><span>桥接库</span><strong>{config.hardware.bridge_library}</strong></div>
        </div>
      </section>

      <section className="panel">
        <h2>电机 ID 映射</h2>
        <div className="kv-list">
          <div><span>全部电机</span><strong>{formatArray(config.hardware.motor_ids)}</strong></div>
          <div><span>驱动电机</span><strong>{formatArray(config.hardware.drive_motor_ids)}</strong></div>
          <div><span>转向电机</span><strong>{formatArray(config.hardware.steer_motor_ids)}</strong></div>
          <div><span>驱动反向</span><strong>{formatArray(config.hardware.inverted_drive_motor_ids)}</strong></div>
          <div><span>驱动轮位</span><strong>{formatRoleMap(config.hardware.drive_motor_roles)}</strong></div>
          <div><span>转向轮位</span><strong>{formatRoleMap(config.hardware.steer_motor_roles)}</strong></div>
        </div>
      </section>

      <section className="panel">
        <h2>控制参数</h2>
        <div className="summary-grid">
          <div><span>最大线速度</span><strong>{config.control.max_linear_speed} m/s</strong></div>
          <div><span>摇杆死区</span><strong>{config.control.deadzone}</strong></div>
          <div><span>速度斜坡</span><strong>{config.control.drive_speed_ramp_mps_per_s} m/s²</strong></div>
          <div><span>mode1 转向轴</span><strong>{config.control.mode1.steering_axis}</strong></div>
          <div><span>mode1 最大内侧角</span><strong>{config.control.mode1.max_inner_steering_degrees}°</strong></div>
          <div><span>mode2 速度比例</span><strong>{config.control.mode2.speed_scale}</strong></div>
        </div>
      </section>

      <section className="panel">
        <h2>远程输入</h2>
        <div className="summary-grid">
          <div><span>监听地址</span><strong>{config.network.bind_host}</strong></div>
          <div><span>UDP 端口</span><strong>{config.network.port}</strong></div>
          <div><span>超时时间</span><strong>{config.network.timeout_s} s</strong></div>
        </div>
      </section>
    </div>
  );
}

export default ConfigCheck;
