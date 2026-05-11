#!/usr/bin/env bash
set -euo pipefail

# 编译 Python 调用的 C++ 桥接共享库。

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"
bridge_dir="$project_root/bridge/cpp"
build_dir="$bridge_dir/build"

if [[ ! -d "$project_root/vendor/damiao_core" ]]; then
  echo "找不到 vendor/damiao_core，无法编译硬件桥接层。" >&2
  exit 1
fi

cmake -S "$bridge_dir" -B "$build_dir"
cmake --build "$build_dir" -j"$(nproc)"

echo "桥接层编译完成: $build_dir/libdm_bridge.so"
