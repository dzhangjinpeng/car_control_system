import { useEffect, useMemo, useState } from 'react';
import { api } from '../apiClient';
import type { CalibrationReport } from '../types';

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return JSON.stringify(value);
}

function Calibration() {
  const [report, setReport] = useState<CalibrationReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchCalibration = async () => {
      const result = await api.getCalibrationLatest();
      if (!mounted) {
        return;
      }
      if (result.ok && result.data) {
        setReport(result.data);
        setError(null);
      } else {
        setError(result.error || '读取校准报告失败');
      }
    };

    fetchCalibration();
    const timer = window.setInterval(fetchCalibration, 2000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const issues = useMemo(() => report?.config_issues || [], [report]);

  if (error) {
    return <div className="alert danger">加载错误：{error}</div>;
  }

  if (!report) {
    return <div className="loading">等待校准报告...</div>;
  }

  return (
    <div className="stack">
      <section className="panel">
        <div className="panel-heading">
          <h2>校准报告</h2>
          <span className={issues.length === 0 ? 'status-pill ok' : 'status-pill danger'}>
            {issues.length === 0 ? '未发现配置问题' : `${issues.length} 个问题`}
          </span>
        </div>
        <div className="summary-grid">
          <div>
            <span>Flash 保存</span>
            <strong>{report.save_flash ? '已保存' : '未保存或未知'}</strong>
          </div>
          <div>
            <span>已校准转向 ID</span>
            <strong>{report.calibrated_steer_ids?.join(', ') || '-'}</strong>
          </div>
          <div>
            <span>反向驱动电机 ID</span>
            <strong>{report.result_inverted_drive_motor_ids?.join(', ') || '-'}</strong>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>实时检查</h2>
        <div className="kv-list">
          {Object.entries(report.live_checks || {}).map(([key, value]) => (
            <div key={key}>
              <span>{key}</span>
              <strong>{formatValue(value)}</strong>
            </div>
          ))}
          {Object.keys(report.live_checks || {}).length === 0 && (
            <p className="empty-text">暂无实时检查结果</p>
          )}
        </div>
      </section>

      <section className="panel">
        <h2>转向零点检查</h2>
        <div className="kv-list">
          {Object.entries(report.steer_zero_checks || {}).map(([key, value]) => (
            <div key={key}>
              <span>{key}</span>
              <strong>{formatValue(value)}</strong>
            </div>
          ))}
          {Object.keys(report.steer_zero_checks || {}).length === 0 && (
            <p className="empty-text">暂无转向零点检查结果</p>
          )}
        </div>
      </section>

      <section className="panel">
        <h2>配置问题与备注</h2>
        {issues.length > 0 ? (
          <ul className="issue-list">
            {issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        ) : (
          <p className="empty-text">未发现配置问题。</p>
        )}
        {(report.notes || []).length > 0 && (
          <ul className="notice-list compact">
            {report.notes?.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default Calibration;
