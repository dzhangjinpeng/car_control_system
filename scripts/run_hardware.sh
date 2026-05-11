#!/usr/bin/env bash
set -euo pipefail

# 真机运行入口。运行前必须确认 configs/hardware.json 参数正确。

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"

input_mode="${1:-gamepad}"
extra_args=()
if [[ $# -gt 1 ]]; then
  extra_args=("${@:2}")
fi

cd "$project_root"
python3 car_control_system.py --input "$input_mode" --telemetry "${extra_args[@]}"
