#!/usr/bin/env bash
set -euo pipefail

# Ubuntu/ARM 板子环境检查与自动安装脚本。

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

have_apt_pkg() {
  dpkg -s "$1" >/dev/null 2>&1
}

ensure_sudo() {
  if [[ "${EUID}" -eq 0 ]]; then
    SUDO=()
  elif need_cmd sudo; then
    SUDO=(sudo)
  else
    echo "缺少 sudo，无法自动安装系统依赖。请手动安装后再运行。" >&2
    exit 1
  fi
}

ensure_apt_packages() {
  local missing=()
  for pkg in "$@"; do
    if ! have_apt_pkg "$pkg"; then
      missing+=("$pkg")
    fi
  done

  if [[ "${#missing[@]}" -eq 0 ]]; then
    return 0
  fi

  ensure_sudo
  "${SUDO[@]}" apt-get update
  "${SUDO[@]}" apt-get install -y "${missing[@]}"
}

ensure_python_package() {
  local module="$1"
  local package="$2"
  if python3 -c "import ${module}" >/dev/null 2>&1; then
    return 0
  fi

  ensure_apt_packages python3-pip
  python3 -m pip install --user "$package"
}

ensure_apt_packages python3 build-essential cmake pkg-config libusb-1.0-0-dev

if [[ "${1:-}" == "--with-gamepad" ]]; then
  ensure_python_package pygame pygame
fi

echo "环境检查完成。"
