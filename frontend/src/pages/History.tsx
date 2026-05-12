import { useEffect, useMemo, useState } from 'react';
import { api } from '../apiClient';
import type { TelemetryFrame } from '../types';

function formatLatency(value: number | null) {
  return value === null ? '-' : value.toFixed(3);
}

function History() {
  const [history, setHistory] = useState<TelemetryFrame[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modeFilter, setModeFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [linkFilter, setLinkFilter] = useState('');

  useEffect(() => {
    const fetchHistory = async () => {
      const result = await api.getHistoryTelemetry(100);
      if (result.ok && result.data) {
        setHistory(result.data);
        setError(null);
      } else {
        setError(result.error || '读取历史遥测失败');
      }
    };
    fetchHistory();
  }, []);

  const filteredHistory = useMemo(() => {
    return history.filter((frame) => {
      if (modeFilter && frame.mode_name !== modeFilter) {
        return false;
      }
      if (sourceFilter && frame.input_source !== sourceFilter) {
        return false;
      }
      if (linkFilter && frame.input_link_state !== linkFilter) {
        return false;
      }
      return true;
    });
  }, [history, linkFilter, modeFilter, sourceFilter]);

  const modes = Array.from(new Set(history.map((frame) => frame.mode_name)));
  const sources = Array.from(new Set(history.map((frame) => frame.input_source)));
  const links = Array.from(new Set(history.map((frame) => frame.input_link_state)));

  if (error) {
    return <div className="alert danger">加载错误：{error}</div>;
  }

  return (
    <section className="panel history-panel">
      <div className="panel-heading">
        <h2>遥测历史</h2>
        <span>最近 {filteredHistory.length} / {history.length} 帧</span>
      </div>

      <div className="filter-bar">
        <label>
          模式
          <select value={modeFilter} onChange={(event) => setModeFilter(event.target.value)}>
            <option value="">全部</option>
            {modes.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
        </label>
        <label>
          输入源
          <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}>
            <option value="">全部</option>
            {sources.map((source) => (
              <option key={source} value={source}>
                {source}
              </option>
            ))}
          </select>
        </label>
        <label>
          链路
          <select value={linkFilter} onChange={(event) => setLinkFilter(event.target.value)}>
            <option value="">全部</option>
            {links.map((link) => (
              <option key={link} value={link}>
                {link}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>循环</th>
              <th>模式</th>
              <th>输入源</th>
              <th>链路</th>
              <th>急停</th>
              <th>延迟(s)</th>
            </tr>
          </thead>
          <tbody>
            {filteredHistory.map((frame) => (
              <tr key={`${frame.timestamp}-${frame.loop_index}`}>
                <td>{new Date(frame.timestamp * 1000).toLocaleTimeString()}</td>
                <td className="mono">{frame.loop_index}</td>
                <td>{frame.mode_name}</td>
                <td>{frame.input_source}</td>
                <td>{frame.input_link_state}</td>
                <td>{frame.emergency_stop ? '是' : '否'}</td>
                <td className="mono">{formatLatency(frame.remote_latency_s)}</td>
              </tr>
            ))}
            {filteredHistory.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-row">
                  没有符合筛选条件的记录
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default History;
