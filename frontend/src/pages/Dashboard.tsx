import { useEffect, useMemo, useState } from 'react';
import { api } from '../apiClient';
import InputDisplay from '../components/InputDisplay';
import MotorTable from '../components/MotorTable';
import type { TelemetryFrame } from '../types';

function linkStateClassName(state: string) {
  if (state.includes('在线') || state.includes('本地')) {
    return 'status-pill ok';
  }
  if (state.includes('超时') || state.includes('无效') || state.includes('急停')) {
    return 'status-pill danger';
  }
  return 'status-pill warn';
}

function formatLatency(value: number | null) {
  if (value === null) {
    return '无远程数据';
  }
  return `${(value * 1000).toFixed(0)} ms`;
}

function Dashboard() {
  const [telemetry, setTelemetry] = useState<TelemetryFrame | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchTelemetry = async () => {
      const result = await api.getLatestTelemetry();
      if (!mounted) {
        return;
      }
      if (result.ok && result.data) {
        setTelemetry(result.data);
        setError(null);
      } else {
        setError(result.error || '读取遥测数据失败');
      }
    };

    fetchTelemetry();
    const timer = window.setInterval(fetchTelemetry, 500);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const noticeLines = useMemo(() => {
    if (!telemetry?.notice) {
      return [];
    }
    return telemetry.notice.split('\n').filter(Boolean);
  }, [telemetry]);

  if (error) {
    return <div className="alert danger">加载错误：{error}</div>;
  }

  if (!telemetry) {
    return <div className="loading">等待后端遥测数据...</div>;
  }

  const latencyHigh = telemetry.remote_latency_s !== null && telemetry.remote_latency_s > 0.2;

  return (
    <div className="dashboard">
      <section className="status-bar">
        <div className="status-group">
          <div>
            <span className="muted">模式</span>
            <strong>{telemetry.mode_name}</strong>
          </div>
          <div>
            <span className="muted">输入源</span>
            <strong>{telemetry.input_source}</strong>
          </div>
          <div>
            <span className="muted">链路</span>
            <span className={linkStateClassName(telemetry.input_link_state)}>
              {telemetry.input_link_state}
            </span>
          </div>
          <div>
            <span className="muted">远程序号</span>
            <strong>{telemetry.remote_seq ?? '-'}</strong>
          </div>
          <div>
            <span className="muted">远程延迟</span>
            <strong className={latencyHigh ? 'warn-text' : undefined}>
              {formatLatency(telemetry.remote_latency_s)}
            </strong>
          </div>
        </div>
        <div className="status-group right">
          {telemetry.remote_stale && <span className="status-pill warn">远程超时</span>}
          {telemetry.emergency_stop && <span className="status-pill danger">急停已触发</span>}
        </div>
      </section>

      <div className="dashboard-grid">
        <section className="panel side-panel">
          <h2>驾驶输入</h2>
          <InputDisplay input={telemetry.driver_input} />
          <div className="summary-row">
            <span>转向锁定</span>
            <strong>{telemetry.steering_locked ? '已锁定' : '未锁定'}</strong>
          </div>
          <div className="summary-row">
            <span>驱动方向</span>
            <strong>{telemetry.drive_direction_name}</strong>
          </div>
        </section>

        <section className="panel notice-panel">
          <h2>系统提示</h2>
          {noticeLines.length > 0 ? (
            <ul className="notice-list">
              {noticeLines.map((line, index) => (
                <li key={`${line}-${index}`}>
                  <span>{new Date(telemetry.timestamp * 1000).toLocaleTimeString()}</span>
                  {line}
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-text">暂无提示</p>
          )}
        </section>

        <section className="panel motor-panel">
          <div className="panel-heading">
            <h2>驱动电机</h2>
            <span>{telemetry.drive_summary}</span>
          </div>
          <MotorTable motors={telemetry.drive_motors} />
        </section>

        <section className="panel motor-panel">
          <div className="panel-heading">
            <h2>转向电机</h2>
            <span>{telemetry.steer_summary}</span>
          </div>
          <MotorTable motors={telemetry.steer_motors} />
        </section>
      </div>
    </div>
  );
}

export default Dashboard;
