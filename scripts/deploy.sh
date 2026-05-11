#!/usr/bin/env bash
set -euo pipefail

# Ubuntu/ARM 板子一键脚本：
# 1. 检查并安装依赖
# 2. 编译 C++ 桥接层
# 3. 可选启动控制程序
usage() {
  cat <<'EOF'
Usage: scripts/deploy.sh [--no-build] [--run] [--mock] [--input MODE] [--control-profile NAME] [--max-loops N] [--telemetry]

Options:
  --no-build       跳过重新编译 C++ 桥接层。
  --run            编译后启动 Python 控制程序。
  --mock           使用内存电机客户端，不走真实硬件桥接层。
  --input MODE     输入模式，neutral、demo 或 gamepad。默认 demo。
  --control-profile NAME
                   选择控制参数挡位，可用 conservative、normal、sport。
  --max-loops N    运行 N 次循环后退出。默认 gamepad 无限制，其它模式 10 次。
  --telemetry      运行时打印实时输入和电机目标。
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"

build_bridge=true
run_app=false
use_mock=false
input_mode="demo"
control_profile="normal"
max_loops=""
telemetry=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      build_bridge=false
      shift
      ;;
    --run)
      run_app=true
      shift
      ;;
    --mock)
      use_mock=true
      shift
      ;;
    --input)
      input_mode="${2:-}"
      shift 2
      ;;
    --control-profile)
      control_profile="${2:-}"
      shift 2
      ;;
    --max-loops)
      max_loops="${2:-}"
      shift 2
      ;;
    --telemetry)
      telemetry=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage
      exit 1
      ;;
  esac
done

setup_args=()
if [[ "$input_mode" == "gamepad" ]]; then
  setup_args+=(--with-gamepad)
fi
"$script_dir/setup_board.sh" "${setup_args[@]}"

if [[ "$build_bridge" == true ]]; then
  "$script_dir/build_bridge.sh"
fi

if [[ "$run_app" == true ]]; then
  cd "$project_root"
  args=()
  if [[ "$use_mock" == true ]]; then
    args+=(--mock)
  fi
  args+=(--input "$input_mode")
  args+=(--control-profile "$control_profile")
  if [[ -n "$max_loops" ]]; then
    args+=(--max-loops "$max_loops")
  fi
  if [[ "$telemetry" == true ]]; then
    args+=(--telemetry)
  fi
  python3 car_control_system.py "${args[@]}"
fi
