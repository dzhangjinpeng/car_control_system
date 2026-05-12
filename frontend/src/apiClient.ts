import type { ApiResponse, CalibrationReport, HealthData, TelemetryFrame } from './types';
import { mockCalibrationReport, mockHealthData, mockTelemetryFrame } from './mockData';

let isMockMode = true;

export const setMockMode = (mock: boolean) => {
  isMockMode = mock;
};

export const getMockMode = () => isMockMode;

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

async function fetchApi<T>(endpoint: string, mockData: T): Promise<ApiResponse<T>> {
  if (isMockMode) {
    // 模拟模式只用于前端本地预览，不会向小车发送任何控制命令。
    await new Promise((resolve) => setTimeout(resolve, 80));
    return { ok: true, data: mockData };
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`);
    const data = (await response.json()) as ApiResponse<T>;
    if (!response.ok && data.error === undefined) {
      return { ok: false, error: `HTTP ${response.status}` };
    }
    return data;
  } catch (error) {
    const message = error instanceof Error ? error.message : '网络请求失败';
    return { ok: false, error: message };
  }
}

export const api = {
  getHealth: () => fetchApi<HealthData>('/health', mockHealthData),
  getLatestTelemetry: () => fetchApi<TelemetryFrame>('/telemetry/latest', mockTelemetryFrame),
  getHistoryTelemetry: (limit = 100) =>
    fetchApi<TelemetryFrame[]>(`/telemetry/history?limit=${limit}`, [mockTelemetryFrame]),
  getCalibrationLatest: () =>
    fetchApi<CalibrationReport>('/calibration/latest', mockCalibrationReport),
};
