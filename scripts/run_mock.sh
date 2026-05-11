#!/usr/bin/env bash
set -euo pipefail

# mock 运行，不接真实硬件，用于验证控制逻辑。

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"

input_mode="${1:-demo}"
max_loops="${2:-5}"
extra_args=()
if [[ $# -gt 2 ]]; then
  extra_args=("${@:3}")
fi

cd "$project_root"
python3 car_control_system.py --mock --input "$input_mode" --max-loops "$max_loops" "${extra_args[@]}"
