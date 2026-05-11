#!/usr/bin/env bash
set -euo pipefail

# 在项目根目录运行纯软件测试，不需要真实小车和 CAN 设备。
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
