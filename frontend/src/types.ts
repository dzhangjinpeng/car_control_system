export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
}

export interface MotorItem {
  role: string;
  motor_id: number;
  target: number;
  actual: number;
  error: number;
  unit: string;
}

export interface DriverInput {
  left_x: number;
  left_y: number;
  right_x: number;
  right_y: number;
  mode_button: boolean;
  steering_lock_button: boolean;
  drive_direction_button: boolean;
  emergency_stop_button: boolean;
}

export interface TelemetryFrame {
  schema_version: number;
  timestamp: number;
  loop_index: number;
  mode_name: string;
  input_source: string;
  input_link_state: string;
  remote_seq: number | null;
  remote_latency_s: number | null;
  remote_stale: boolean | null;
  steering_locked: boolean;
  drive_direction_name: string;
  emergency_stop: boolean;
  driver_input: DriverInput;
  drive_summary: string;
  steer_summary: string;
  drive_motors: MotorItem[];
  steer_motors: MotorItem[];
  notice: string;
}

export interface StartupChecks {
  bridge_library_exists: boolean;
  calibration_report_exists: boolean;
  hardware_issues: string[];
  control_issues: string[];
  config_issues: string[];
  ok: boolean;
}

export interface HealthData {
  service: string;
  schema_version: number;
  telemetry_ready: boolean;
  latest_loop_index: number | null;
  mode_name: string | null;
  input_source: string | null;
  input_link_state: string | null;
  startup_checks: StartupChecks;
  config_issues: string[];
}

export interface CalibrationReport {
  hardware_config?: unknown;
  config_issues?: string[];
  live_checks?: Record<string, unknown>;
  drive_direction_result?: Record<string, unknown>;
  calibrated_steer_ids?: number[];
  steer_zero_checks?: Record<string, unknown>;
  result_inverted_drive_motor_ids?: number[];
  save_flash?: boolean;
  notes?: string[];
}

export type AppPage = 'dashboard' | 'calibration' | 'history';
