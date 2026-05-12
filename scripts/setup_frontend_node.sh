#!/usr/bin/env bash
set -euo pipefail

required_major=20

current_major() {
  if ! command -v node >/dev/null 2>&1; then
    echo 0
    return
  fi
  node -p "Number(process.versions.node.split('.')[0])"
}

major="$(current_major)"
if [[ "$major" -ge "$required_major" ]]; then
  echo "Node.js 版本满足要求：$(node -v)"
  echo "npm 版本：$(npm -v)"
  exit 0
fi

if [[ "$major" -eq 0 ]]; then
  echo "未检测到 Node.js，准备安装 Node.js 20。"
else
  echo "当前 Node.js 版本过低：$(node -v)，准备升级到 Node.js 20。"
fi

if [[ "${EUID}" -eq 0 ]]; then
  apt-get update
  apt-get install -y ca-certificates curl gnupg
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
else
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

echo "Node.js 安装完成：$(node -v)"
echo "npm 版本：$(npm -v)"
