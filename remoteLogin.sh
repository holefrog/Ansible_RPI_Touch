#!/bin/bash
set -euo pipefail

# ==========================================================
# 1. 配置常量
# ==========================================================
HOST="192.168.50.207"
PORT="22"
USER="player"
# 你的相对路径
RELATIVE_KEY="./rpi_keys/id_rpi"
SSH_PASS=""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# ==========================================================
# 2. 路径转换与权限检查
# ==========================================================
# 切换到脚本所在目录，确保相对路径基准正确
cd "$(dirname "$0")"

if [[ -n "$RELATIVE_KEY" ]]; then
    # 转换为绝对路径
    ABS_KEY="$(pwd)/${RELATIVE_KEY#./}"
    
    if [[ ! -f "$ABS_KEY" ]]; then
        echo -e "${RED}[错误] 未找到密钥文件: $ABS_KEY${NC}"
        exit 1
    fi
    
    # 按照你的习惯，强制修正权限
    chmod 400 "$ABS_KEY"
    SSH_CMD="ssh -i $ABS_KEY"
else
    SSH_CMD="ssh"
fi

SSH_OPTS="-p $PORT -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o IdentitiesOnly=yes"
REMOTE="$USER@$HOST"

# ==========================================================
# 3. 执行登录
# ==========================================================
echo -e "${GREEN}>>> 正在连接 $HOST (端口: $PORT)...${NC}"

# 清理旧条目
ssh-keygen -f "$HOME/.ssh/known_hosts" -R "$HOST" >/dev/null 2>&1 || true

# 正式进入
TERM=xterm-256color $SSH_CMD $SSH_OPTS "$REMOTE"

echo -e "${NC}>>> 已断开连接。${NC}"
