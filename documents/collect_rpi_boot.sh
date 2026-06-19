#!/bin/bash

# 配置变量
RPI_USER="player"
RPI_IP="192.168.50.207"
REMOTE_TMP_FILE="/tmp/rpi_boot_analysis.txt"
LOCAL_TARGET_DIR="."

echo "===================================================="
echo "开始持续侦测树莓派 ($RPI_IP) 的启动状态..."
echo "===================================================="

# 1. 循环检测 Ping，直到网络通路
while ! ping -c 1 -W 1 "$RPI_IP" &> /dev/null; do
    sleep 0.5
done

echo "[$(date +%T)] 探测到树莓派网络已连通！"
echo "正在等待 SSH 服务响应..."

# 2. 循环检测 SSH 22 端口，防止 sshd 未完全拉起导致连接断开
while ! nc -z -w 1 "$RPI_IP" 22 &> /dev/null; do
    sleep 0.5
done

echo "[$(date +%T)] SSH 端口已开放，开始远程连接..."

# 3. 通过通道和 SSH 远程执行命令
ssh "${RPI_USER}@${RPI_IP}" << EOF
    echo "[树莓派端] 已建立连接，正在等待 systemd 核心用户空间完全初始化完毕..."
    
    # 循环检查系统启动状态，直到 userspace 彻底跑完（退出 initializing 或 starting 状态）
    while [[ "\$(systemctl is-system-running 2>/dev/null)" == "initializing" || "\$(systemctl is-system-running 2>/dev/null)" == "starting" ]]; do
        sleep 0.5
    done

    echo "[树莓派端] 系统已完全就绪（\$(systemctl is-system-running)），开始打包生成最终报告..."

    echo "--- 1. 总体启动耗时 ---" > "${REMOTE_TMP_FILE}"
    systemd-analyze >> "${REMOTE_TMP_FILE}" 2>&1
    
    echo -e "\n--- 2. 服务耗时降序排名 (Blame) ---" >> "${REMOTE_TMP_FILE}"
    systemd-analyze blame | head -n 30 >> "${REMOTE_TMP_FILE}" 2>&1
    
    echo -e "\n--- 3. 核心启动关键链 ---" >> "${REMOTE_TMP_FILE}"
    systemd-analyze critical-chain >> "${REMOTE_TMP_FILE}" 2>&1
    
    echo -e "\n--- 4. 闪屏服务关键链 ---" >> "${REMOTE_TMP_FILE}"
    systemd-analyze critical-chain splash_service.service >> "${REMOTE_TMP_FILE}" 2>&1
    
    echo -e "\n--- 5. 闪屏服务本次开机日志 ---" >> "${REMOTE_TMP_FILE}"
    sudo journalctl -u splash_service.service -b 0 --no-pager | head -n 50 >> "${REMOTE_TMP_FILE}" 2>&1
EOF

if [ $? -eq 0 ]; then
    echo "[$(date +%T)] 树莓派端数据收集完成。"
else
    echo "[错误] 远程命令执行失败，请检查 SSH 免密登录配置。"
    exit 1
fi

# 4. 使用 scp 将生成的分析报告拉取到主机的当前目录下
echo "正在将分析文件拖回主机..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOCAL_FILE="${LOCAL_TARGET_DIR}/rpi_boot_report_${TIMESTAMP}.txt"

scp "${RPI_USER}@${RPI_IP}:${REMOTE_TMP_FILE}" "${LOCAL_FILE}"

if [ $? -eq 0 ]; then
    echo "===================================================="
    echo "成功！启动分析报告已保存至: ${LOCAL_FILE}"
    echo "===================================================="
    # 清理树莓派上的临时文件
    ssh "${RPI_USER}@${RPI_IP}" "rm -f ${REMOTE_TMP_FILE}"
else
    echo "[错误] SCP 文件传输失败。"
    exit 1
fi
