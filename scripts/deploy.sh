#!/usr/bin/env bash
set -euo pipefail

# Ubuntu/ARM 板子一键脚本：
# 1. 检查并安装依赖
# 2. 编译 C++ 桥接层
# 3. 可选启动控制程序
usage() {
  cat <<'EOF'
Usage: scripts/deploy.sh [--no-build] [--run] [--mock] [--input MODE] [--control-profile NAME] [--max-loops N] [--telemetry] [--api]

Options:
  --no-build       跳过重新编译 C++ 桥接层。
  --run            编译后启动 Python 控制程序。
  --mock           使用内存电机客户端，不走真实硬件桥接层。
  --input MODE     输入模式，neutral、demo、gamepad、remote 或 hybrid。默认 demo。
  --control-profile NAME
                   选择控制参数挡位，可用 conservative、normal、sport。
  --max-loops N    运行 N 次循环后退出。默认 gamepad 无限制，其它模式 10 次。
  --telemetry      运行时打印实时输入和电机目标。
  --api            同时启动给前端用的只读 HTTP 接口。
  --api-host HOST  API 绑定地址，默认 127.0.0.1。
  --api-port PORT  API 端口，默认 8765。
  --api-history-size N
                   API 历史缓存长度，默认 200。
  --calibration-report PATH
                   校准报告路径，默认 logs/calibration.json。
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
api=false
api_host="127.0.0.1"
api_port="8765"
api_history_size="200"
calibration_report="logs/calibration.json"

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
    --api)
      api=true
      shift
      ;;
    --api-host)
      api_host="${2:-}"
      shift 2
      ;;
    --api-port)
      api_port="${2:-}"
      shift 2
      ;;
    --api-history-size)
      api_history_size="${2:-}"
      shift 2
      ;;
    --calibration-report)
      calibration_report="${2:-}"
      shift 2
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
  if [[ "$api" == true ]]; then
    args+=(--api)
    args+=(--api-host "$api_host")
    args+=(--api-port "$api_port")
    args+=(--api-history-size "$api_history_size")
    args+=(--calibration-report "$calibration_report")
  fi
  python3 car_control_system.py "${args[@]}"
fi
