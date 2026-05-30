![Logo](logo.png)

# 🎵 RPI MediaPlayer (Ansible Edition)

将 Raspberry Pi 打造为专业级多音源媒体播放器，支持 **Logitech Media Server (LMS)**、**AirPlay 2** 和 **蓝牙音频**，配备 **OLED 实时显示屏**。本项目已重构为基于 **Ansible** 的全自动化部署架构。

---

## ✨ 核心特性

### 🎼 三音源无缝切换
- **🎹 Squeezelite** - 连接 Logitech Media Server，播放本地音乐库
- **📱 AirPlay 2** - 从 iPhone/iPad/Mac 推送音频
- **🔵 蓝牙音箱** - 接收任何蓝牙设备的音频流

### 🖥️ 智能 OLED 显示
- 📊 实时显示当前音源（SQ/AP/BT）
- 🎨 艺术家、曲目信息自动滚动
- 🔊 音量调节时弹窗显示
- 💤 智能屏保（5秒暗屏，15分钟关闭）

### 🔊 专业音频处理
- **PipeWire** - 现代音频服务器
- **WM8960 声卡** - 高保真输出
- 🎚️ 音源优先级自动管理
- 🎛️ 独立音量控制

### 🚀 Ansible 自动化部署
- ⚡ 一键执行 Playbook
- 🔄 声明式配置，自动处理依赖和顺序
- 🔌 硬件驱动自动加载
- ✅ 幂等性（重复执行不破坏现有环境）

---

## 🧩 硬件需求

| 组件 | 推荐型号 | 必需 |
|------|---------|:----:|
| **主板** | Raspberry Pi 4B (4GB) | ✅ |
| **声卡** | Waveshare WM8960 Audio Board | ✅ |
| **显示屏** | SSD1306 OLED (128x64, I2C) | ⭕ |
| **电源** | 5V 3A USB-C | ✅ |
| **存储** | microSD 卡 (16GB+) | ✅ |

> **⚠️ 重要提示：**
> - WM8960 是 **Sound Board**，不是 Audio HAT，接线方式不同
> - OLED 使用 GPIO 模拟 I2C（I2C-3），不占用标准 I2C 总线
> - 详细接线图请参见 [`documents/HW_WM8960.md`](documents/HW_WM8960.md) 和 [`documents/HW_SSD1306.md`](documents/HW_SSD1306.md)

---

## 💽 操作系统

**推荐：Raspberry Pi OS Trixie (64-bit)** 或 **Bookworm (64-bit)**

> **⚠️ 重要：** Trixie/Bookworm 不再支持 `wpa_supplicant.conf` 配置 WiFi  
> 必须使用 **Raspberry Pi Imager** 的预配置功能

📖 详细无头安装步骤：[`documents/RPI_HEADLESS_SETUP.md`](documents/RPI_HEADLESS_SETUP.md)

---

## 📁 项目结构

```text
RPI-MediaPlayer/
├── ansible/
│   ├── ansible.cfg              # Ansible 全局配置
│   ├── site.yml                 # 主 Playbook 入口
│   ├── status.yml               # 服务状态检查 Playbook
│   ├── inventory/
│   │   └── hosts.ini            # 目标主机清单与连接配置
│   ├── group_vars/
│   │   └── all.yml              # 全局变量配置（LMS IP、用户信息等）
│   └── roles/                   # Ansible 角色模块
│       ├── system/              # 系统基础与硬件配置 (WM8960, OLED I2C)
│       ├── pipewire/            # PipeWire 音频服务器
│       ├── volume/              # 硬件与软件音量控制
│       ├── squeezelite/         # LMS 客户端
│       ├── airplay/             # Shairport-Sync (AirPlay 2)
│       ├── bluetooth/           # 蓝牙音频与自动配对
│       └── oled/                # OLED 状态显示 Python 应用
│
├── documents/                   # 详细文档
│   ├── BLUETOOTH_TIPS.md        # 蓝牙配提示
│   ├── HW_SSD1306.md            # OLED 接线和配置
│   ├── HW_WM8960.md             # WM8960 接线和验证
│   ├── RPI_HEADLESS_SETUP.md    # 无头安装教程
│   ├── RPI_SSH_KEY_GEN.md       # SSH 密钥配置
│   └── TROUBLESHOOTING.md       # 故障排查指南
│
├── rpi_keys/                    # SSH 密钥存放目录（请勿提交私钥）
├── apply.sh                     # 一键执行部署脚本
├── remoteLogin.sh               # 快捷 SSH 登录脚本
└── README.md                    # 本文档
```

---

## 🚀 部署流程

### 前置要求

- ✅ 你的本地电脑已安装 **Ansible** (`sudo apt install ansible` 或 `brew install ansible`)
- ✅ 已安装 Raspberry Pi OS 并接入网络
- ✅ 已配置 SSH 并可通过 `rpi.local` 或 IP 访问

### 快速开始

在 **本地电脑**（非树莓派）执行以下命令：

```bash
# 1️⃣ 克隆仓库
git clone https://github.com/yourusername/RPI-MediaPlayer.git
cd RPI-MediaPlayer

# 2️⃣ 创建 SSH 密钥（如果没有，也可以使用已有的密钥）
mkdir -p rpi_keys
ssh-keygen -t ed25519 -f ./rpi_keys/id_rpi -C "player@rpi"
# 按 Enter 跳过密码（用于无密码登录）

# 3️⃣ 将公钥复制到树莓派 (替换下面的IP和用户名为你的实际配置)
ssh-copy-id -i ./rpi_keys/id_rpi.pub player@rpi.local

# 4️⃣ 配置 Ansible 主机
nano ansible/inventory/hosts.ini
```

**编辑 `hosts.ini` 示例：**
```ini
[mediaplayers]
rpi.local ansible_user=player ansible_ssh_private_key_file=../rpi_keys/id_rpi

[mediaplayers:vars]
ansible_python_interpreter=/usr/bin/python3
```

**编辑全局变量（可选）：**
```bash
nano ansible/group_vars/all.yml
# 可以在此处修改 lms_server_ip 等参数
```

```bash
# 5️⃣ 运行 Ansible 自动化部署
./apply.sh
# (或者直接运行: ansible-playbook -i ansible/inventory/hosts.ini ansible/site.yml -K)
```

> **注意：** 部署过程中如果涉及到硬件配置的更改，Ansible 可能会自动重启树莓派。由于重构为了 Ansible Playbook，整个过程是自动管理且幂等的。

---

## 📊 系统服务

部署完成后，可以使用以下命令检查各服务的运行状态：

```bash
ansible-playbook -i ansible/inventory/hosts.ini ansible/status.yml
```

### 主要后台服务：

- **系统级服务：**
  - `bluetooth.service` - 蓝牙底层服务
  - `bluetooth-a2dp-autopair.service` - 蓝牙自动配对代理
- **用户级服务：**
  - `pipewire.service` - 核心音频服务器
  - `squeezelite.service` - LMS 播放器
  - `shairport-sync.service` - AirPlay 接收服务
  - `oled.service` - 显示屏驱动程序
  - `volume.service` - 音量监听器

---

## 🎮 使用指南

### 🎵 播放音乐

#### 方式 1：Logitech Media Server (LMS)
1. 在 LMS 服务器上找到你的播放器
2. 选择音乐并播放
3. OLED 显示屏会自动显示曲目信息

#### 方式 2：AirPlay
1. 打开 iPhone/iPad 控制中心
2. 点击 AirPlay 图标，选择播放器
3. 播放音乐，树莓派自动接收

#### 方式 3：蓝牙
1. 打开手机蓝牙设置
2. 搜索并连接 `RPI-Bluetooth`（或在 role 变量中自定义的名称）
3. 无需 PIN 码，自动配对即可播放

### 🔊 音量控制

音量控制已完全集成在系统中：
- **AirPlay**：通过 iOS 设备侧边按键调节
- **蓝牙**：通过播放设备音量键调节
- **Squeezelite**：通过 LMS 界面调节

### 🖥️ OLED 显示说明

**音源标识：**
- `SQ:` - Squeezelite (LMS)
- `AP:` - AirPlay
- `BT:` - 蓝牙

**屏保功能：**
- **5秒无操作** → 亮度降低
- **15分钟无操作** → 屏幕关闭
- **有新活动** → 自动唤醒

---

## 🛠️ 故障排查

详细的故障排查请参阅 [TROUBLESHOOTING.md](documents/TROUBLESHOOTING.md) 

### 常用日志排查命令
```bash
# 查看用户服务日志 (Squeezelite / Shairport / OLED 等)
journalctl --user -u squeezelite -f
journalctl --user -u oled -f

# 查看系统级服务日志 (Bluetooth 等)
journalctl -u bluetooth-a2dp-autopair -f
```

---

## 🤝 贡献与许可

- **开发指南：** 在 `ansible/roles` 目录下开发新模块，确保角色的独立性和高内聚。
- **许可证：** MIT License - 自由使用和修改。

<div align="center">

**🎉 享受您的多功能媒体播放器！**

Made with ❤️ by the RPI MediaPlayer Team

</div>
