#!/usr/bin/env bash
set -euo pipefail

run_hardware=false
if [[ "${1:-}" == "--hardware" ]]; then
  run_hardware=true
fi

timestamp="$(date +%Y%m%d_%H%M%S)"
log_dir="onsite_logs/${timestamp}"
mkdir -p "${log_dir}"

echo "现场检查日志目录：${log_dir}"

run_and_capture() {
  local name="$1"
  shift
  echo ">>> ${name}"
  {
    echo "\$ $*"
    "$@"
  } >"${log_dir}/${name}.txt" 2>&1 || true
}

# 基础环境检查，不接触真实电机。
run_and_capture "git_status" git status
run_and_capture "git_log" git log --oneline -5
run_and_capture "python_version" python3 --version
run_and_capture "node_version" bash -lc 'node -v && npm -v'
run_and_capture "gamepad_list" python3 car_control_system.py --list-gamepads

# 手柄原始轴检测是交互式的，这里只给 20 秒采样窗口，避免脚本一直卡住。
echo ">>> gamepad_axes_sample"
echo "请在接下来的 20 秒内依次动左右摇杆，并按几个关键按钮。"
timeout 20s python3 scripts/inspect_gamepad.py >"${log_dir}/gamepad_axes_sample.txt" 2>&1 || true

# mock 检查只走模拟硬件，确认主程序、配置、控制循环能跑。
run_and_capture "mock_neutral" python3 car_control_system.py --mock --input neutral --telemetry --max-loops 5
run_and_capture "mock_demo_api" python3 car_control_system.py --mock --input demo --api --telemetry --max-loops 5

if [[ "${run_hardware}" == true ]]; then
  echo ">>> hardware_check"
  echo "即将执行硬件检查，请确认 CANFD、电机供电、急停和安全支架已准备好。"
  python3 scripts/calibrate_hardware.py --verify --verify-steer-zero --report-file "${log_dir}/calibration.json" \
    >"${log_dir}/hardware_check.txt" 2>&1 || true
else
  cat >"${log_dir}/hardware_check_skipped.txt" <<'EOF'
未执行硬件检查。
如需检查 CANFD 和电机，请确认硬件安全后运行：

  bash scripts/onsite_check.sh --hardware
EOF
fi

echo "现场检查完成：${log_dir}"
echo "如果要把日志推给我分析："
echo "  git add ${log_dir}"
echo "  git commit -m \"Add onsite check logs\""
echo "  git push"
