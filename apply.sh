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
read -rp "请选择 [1/2，直接回车默认 1 Deploy]: " choice

case "$choice" in
    1|"")
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
KEY="${SCRIPT_DIR}/rpi_keys/id_rpi"
if [[ ! -f "$KEY" ]]; then
    echo "⚠️ 未找到 SSH 私钥: ${KEY}"
    read -rp "是否自动生成新的 SSH 密钥？[y/N]: " gen_key
    if [[ "$gen_key" =~ ^[Yy]$ ]]; then
        mkdir -p "${SCRIPT_DIR}/rpi_keys"
        ssh-keygen -t ed25519 -f "$KEY" -N ""
        echo "✅ 密钥已生成。"
    else
        echo "❌ 请先生成密钥并放入 rpi_keys/ 目录 (例如: ssh-keygen -t ed25519 -f ./rpi_keys/id_rpi)"
        exit 1
    fi
fi
chmod 400 "$KEY"

read -rp "是否需要将公钥复制到目标树莓派 (ssh-copy-id)？[y/N]: " copy_key
if [[ "$copy_key" =~ ^[Yy]$ ]]; then
    read -rp "请输入目标树莓派 (例如 player@192.168.50.207): " target_host
    if [[ -n "$target_host" ]]; then
        # 提取目标 IP (处理包含 user@ 的情况)
        actual_host="${target_host#*@}"
        echo ">>> 清理本地 known_hosts 中的旧密钥记录..."
        ssh-keygen -f "$HOME/.ssh/known_hosts" -R "$actual_host" >/dev/null 2>&1 || true
        echo ">>> 执行 ssh-copy-id -i ${KEY}.pub ${target_host}"
        ssh-copy-id -o StrictHostKeyChecking=no -i "${KEY}.pub" "$target_host"
    else
        echo "未输入目标，跳过。"
    fi
    echo ""
fi

# 进入 ansible 目录以加载 ansible.cfg
cd ansible

echo "--------------------------------------------------------"
echo "🛠️  正在执行 ${MODE}..."
echo "--------------------------------------------------------"

ansible-playbook "$PB" $VERBOSE $BECOME_PASS "$@"

echo ""
echo "🎉 ${MODE} 完成！"
