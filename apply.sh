#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "--------------------------------------------------------"
echo "🚀 RPI MediaPlayer 部署与管理系统"
echo "--------------------------------------------------------"
echo "1) Deploy      - 执行完整部署 (site.yml)"
echo "2) Status      - 检查服务状态 (status.yml)"
echo "--------------------------------------------------------"
read -rp "请选择 [1/2，其他退出]: " choice

case "$choice" in
    1)
        MODE="Deploy"
        PB="site.yml"
        ;;
    2)
        MODE="Status"
        PB="status.yml"
        ;;
    *)
        echo "已退出。"
        exit 0
        ;;
esac

echo ">>> 已选择: ${MODE}"
echo ""

# 检查是否开启 verbose
VERBOSE=""
read -rp "是否开启详细输出 verbose？[y/N]: " v
if [[ "$v" =~ ^[Yy]$ ]]; then
    VERBOSE="-v"
fi
echo ""

BECOME_PASS=""
read -rp "是否需要输入 sudo 密码 (用于 become)？[y/N]: " bp
if [[ "$bp" =~ ^[Yy]$ ]]; then
    BECOME_PASS="-K"
fi
echo ""

# 检查 SSH 密钥
KEY="rpi_keys/id_rpi"
if [[ ! -f "$KEY" ]]; then
    echo "❌ 未找到 SSH 私钥: ${KEY}"
    echo "💡 请先生成密钥并放入 rpi_keys/ 目录 (例如: ssh-keygen -t ed25519 -f ./rpi_keys/id_rpi)"
    exit 1
fi
chmod 400 "$KEY"

# 进入 ansible 目录以加载 ansible.cfg
cd ansible

echo "--------------------------------------------------------"
echo "🛠️  正在执行 ${MODE}..."
echo "--------------------------------------------------------"

ansible-playbook "$PB" $VERBOSE $BECOME_PASS "$@"

echo ""
echo "🎉 ${MODE} 完成！"
