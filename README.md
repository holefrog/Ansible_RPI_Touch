# 🎵 Ansible_RPI_TouchPlayer

将 Raspberry Pi 4B 打造为支持多音源的专业级无头 (Headless) 媒体播放器，配备 2.8 寸全彩触控屏。本项目基于 Ansible 实现全自动化、幂等性部署，并采用“纯 Python 轻量化”图形交互架构。

---

## ✨ 核心特性

### 🎼 多音源无缝切换
* **🎹 Squeezelite** - 连接 Logitech Media Server (LMS)，播放本地/流媒体音乐库。
* **📱 AirPlay 2** - 从 iPhone/iPad/Mac 无缝推送音频 (基于 `shairport-sync`)。
* **🔵 蓝牙音频** - 接收任何蓝牙设备的音频流 (支持自动配对与 A2DP)。

### 🔊 专业音频底层
* **PipeWire** - 采用现代音频服务器，取代老旧的 PulseAudio/ALSA 架构。
* **WM8960 声卡** - 独占标准 I2C-1 (控制) 与 I2S (音频流)，提供高保真音频输出。

### 🖥️ 极简触控交互 (纯 Python 轻量架构)
放弃沉重的系统级图形框架 (如 Pygame/Tkinter)，从底层榨取性能：
* **高速画面推流**：使用 `spidev` 配合 `Pillow` 进行内存绘图，并利用 `NumPy` 向量化极速完成 RGB888 到 16位大端序 RGB565 的转换。
* **无感触控轮询**：摒弃复杂且容易引起事件风暴的硬件中断，使用 `smbus2` 对 FT6336U 触摸芯片 (软件 I2C-3) 进行同步轮询。
* **全屏隐形热区盲操**：专为 2.8 寸小屏设计，放弃传统微小 UI 按钮，将屏幕划分为“左/中/右”三大隐形热区，彻底解决“胖手指”误触痛点。
* **硬件级无闪调光**：屏幕背光直连 BCM 13 (硬件 PWM1)，实现丝滑的智能屏保渐暗效果。

---

## 🧩 硬件需求与引脚分配

| 组件 | 推荐型号 | 必需 |
| :--- | :--- | :--- |
| **主板** | Raspberry Pi 4B (4GB/8GB) | ✅ |
| **声卡** | Waveshare WM8960 Audio Board | ✅ |
| **显示屏** | 2.8寸 SPI 触控屏 (ST7789主控 + FT6336U触控) | ✅ |
| **电源** | 5V 3A USB-C 原装电源 | ✅ |

### ⚠️ 核心防冲突接线指南

本项目经过精密的硬件重构，完美解决了 WM8960 音频板与 SPI 屏幕之间的硬件冲突：

1. **背光冲突避让**：SPI 屏幕默认的背光引脚 (LCD_BL) 常为 BCM 18，但该引脚已被 WM8960 的 I2S CLK 独占。**必须将屏幕背光引脚飞线至 BCM 13 (物理引脚 33)**。
2. **触控总线隔离**：FT6336U 触控芯片使用 GPIO 模拟的 I2C-3 (BCM 4 / BCM 5)，与音频控制的 I2C-1 物理隔离。
3. **中断引脚悬空**：采用轮询模式，**触摸中断引脚 (TP_INT) 无需连接**。

| RPi 物理 PIN | BCM 引脚 | 目标组件引脚 | 说明 |
| :--- | :--- | :--- | :--- |
| **12** | **BCM 18** | WM8960 I2S CLK | 音频位时钟 (已被音频独占) |
| **33** | **BCM 13** | 屏幕 LCD_BL | **背光控制 (硬件 PWM1 完美避让)** |
| **7** | BCM 4 | 触摸 SDA | 模拟 I2C-3 数据线 |
| **29** | BCM 5 | 触摸 SCL | 模拟 I2C-3 时钟线 |

---

## 📁 项目架构 (Ansible Roles)

```text
Ansible_RPI_TouchPlayer/
├── ansible/
│   ├── group_vars/
│   │   └── all.yml             # 全局配置 (如音量限制、引脚定义)
│   ├── roles/
│   │   ├── system_base/        # 基础环境、系统时区、网络调优
│   │   ├── audio_core/         # PipeWire, WM8960驱动, 三大音源服务
│   │   └── gui_touch/          # Python 虚拟环境, NumPy/Pillow/spidev 依赖, 触控主循环及 systemd 服务
│   ├── site.yml                # 主控 Playbook
│   └── hosts.ini               # 目标主机清单
├── scripts/                    # Python 核心绘图与触控轮询代码
└── README.md                   # 项目说明
```

---

## 🚀 自动化部署流程

### 1. 前置要求
* 目标树莓派已安装 **Raspberry Pi OS Bookworm (64-bit) Lite** 无头版本。
* 本地控制端已安装 `ansible`。
* 树莓派已接入网络，且可通过 SSH 免密登录。

### 2. 快速开始
在**本地电脑** (非树莓派) 执行：

```bash
# 克隆本仓库
git clone [https://github.com/holefrog/Ansible_RPI_TouchPlayer.git](https://github.com/holefrog/Ansible_RPI_TouchPlayer.git)
cd Ansible_RPI_TouchPlayer/ansible

# 拷贝并修改主机配置
cp hosts.ini.example hosts.ini
nano hosts.ini  # 填入树莓派的 IP 地址

# 一键部署
ansible-playbook -i hosts.ini site.yml
```

---

## 🛠 开发与调试

如果需要调整 UI 布局或触控热区，只需修改 `scripts/` 目录下的 Python 核心文件。部署后可使用以下命令查看日志：

```bash
# 查看 UI 触控与推帧日志
journalctl -u touch_gui.service -f

# 检查底层音频服务
journalctl -u pipewire.service -f
```

## 🤝 贡献与许可
* **许可证：** MIT License
* Made with ❤️ for the maker community.
