import type { CalibrationReport, HealthData, TelemetryFrame } from './types';

export const mockTelemetryFrame: TelemetryFrame = {
  schema_version: 1,
  timestamp: Date.now() / 1000,
  loop_index: 1024,
  mode_name: 'mode1_ackermann',
  input_source: 'hybrid',
  input_link_state: '远程在线',
  remote_seq: 42,
  remote_latency_s: 0.045,
  remote_stale: false,
  steering_locked: false,
  drive_direction_name: '前进',
  emergency_stop: false,
  driver_input: {
    left_x: -0.35,
    left_y: 0.72,
    right_x: 0.0,
    right_y: 0.0,
    mode_button: false,
    steering_lock_button: false,
    drive_direction_button: false,
    emergency_stop_button: false,
  },
  drive_summary: '驱动目标正常',
  steer_summary: '转向目标正常',
  drive_motors: [
    { role: 'front_left', motor_id: 1, target: 0.48, actual: 0.46, error: 0.02, unit: 'm/s' },
    { role: 'front_right', motor_id: 2, target: 0.52, actual: 0.5, error: 0.02, unit: 'm/s' },
    { role: 'rear_left', motor_id: 3, target: 0.48, actual: 0.47, error: 0.01, unit: 'm/s' },
    { role: 'rear_right', motor_id: 4, target: 0.52, actual: 0.51, error: 0.01, unit: 'm/s' },
  ],
  steer_motors: [
    { role: 'front_left', motor_id: 5, target: -18.2, actual: -17.8, error: -0.4, unit: 'deg' },
    { role: 'front_right', motor_id: 6, target: -14.6, actual: -14.3, error: -0.3, unit: 'deg' },
  ],
  notice: '模拟数据：前端未连接真实后端时用于检查页面布局。',
};

export const mockHealthData: HealthData = {
  service: 'car-control-api',
  schema_version: 1,
  telemetry_ready: true,
  latest_loop_index: mockTelemetryFrame.loop_index,
  mode_name: mockTelemetryFrame.mode_name,
  input_source: mockTelemetryFrame.input_source,
  input_link_state: mockTelemetryFrame.input_link_state,
  startup_checks: {
    bridge_library_exists: true,
    calibration_report_exists: true,
    hardware_issues: [],
    control_issues: [],
    config_issues: [],
    ok: true,
  },
  config_issues: [],
};

export const mockCalibrationReport: CalibrationReport = {
  config_issues: [],
  live_checks: {
    canfd_bridge: 'OK',
    drive_motors: 'OK',
    steer_motors: 'OK',
  },
  drive_direction_result: {
    status: 'OK',
    message: '模拟：驱动方向检查通过',
  },
  calibrated_steer_ids: [5, 6],
  steer_zero_checks: {
    front_left: 'OK',
    front_right: 'OK',
  },
  result_inverted_drive_motor_ids: [],
  save_flash: true,
  notes: ['模拟报告仅用于前端展示，真实校准结果来自后端报告文件。'],
};
