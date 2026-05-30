# 🎵 Ansible_RPI_TouchPlayer

将 Raspberry Pi 4B 打造为专业级多音源媒体播放器，支持 **Logitech Media Server (LMS)**、**AirPlay 2** 和 **蓝牙音频**，配备 **2.8 寸全彩触控屏**。本项目基于 **Ansible** 实现全自动化、幂等性部署，并采用“纯 Python 轻量化”图形交互架构。

---

## ✨ 核心特性

### 🎼 三音源无缝切换
- **🎹 Squeezelite** - 连接 Logitech Media Server，播放本地与流媒体音乐库
- **📱 AirPlay 2** - 从 iPhone/iPad/Mac 无缝推送音频 (基于 `shairport-sync`)
- **🔵 蓝牙音频** - 接收任何蓝牙设备的音频流 (支持自动配对与 A2DP)

### 🖥️ 极简触控交互 (纯 Python 轻量架构)
放弃沉重的系统级图形框架，从底层榨取性能：
- 🚀 **高速画面推流**：`spidev` 配合 `Pillow` 内存绘图，`NumPy` 向量化极速转换 RGB565。
- 👆 **无感触控轮询**：摒弃中断，使用 `smbus2` 对触控芯片 (软 I2C) 进行同步轮询。
- 盲操 UX 设计**：全屏切分为“左/中/右”三大隐形热区，彻底解决“胖手指”误触痛点。
- 💡 **硬件级无闪调光**：屏幕背光直连硬件 PWM 通道，实现丝滑的智能屏保渐暗效果。

### 🔊 专业音频处理
- **PipeWire** - 采用现代音频服务器，取代老旧的 PulseAudio/ALSA 架构
- **WM8960 声卡** - 独占标准 I2C 与 I2S 总线，提供高保真音频输出

---

## 🧩 硬件需求

| 组件 | 推荐型号 | 必需 |
|------|---------|:----:|
| **主板** | Raspberry Pi 4B (4GB/8GB) | ✅ |
| **声卡** | Waveshare WM8960 Audio Board | ✅ |
| **显示屏** | 2.8寸 SPI 触控屏 (ST7789主控 + FT6336U触控) | ✅ |
| **电源** | 5V 3A USB-C 原装电源 | ✅ |
| **存储** | microSD 卡 (16GB+) | ✅ |

> **⚠️ 核心防冲突设计说明：**
> 1. **无需录音**：本项目定位为纯播放器，已精简 WM8960 的录音引脚 (ADC/DIN)，极大简化接线。
> 2. **背光冲突避让**：屏幕背光引脚 (LCD_BL) 必须飞线至 **BCM 13**，严禁使用默认的 BCM 18，以免导致音频时钟崩溃。
> 3. **触控总线隔离**：FT6336U 采用模拟 I2C-3，与音频板的硬件 I2C-1 完全物理隔离。
> 4. **中断引脚悬空**：触控采用主循环同步轮询，**TP_INT 悬空不接**。

---

## 🛠️ 详细硬件接线指南

### 1. WM8960 音频板 (仅播放配置)
作为核心发声单元，独占硬件 I2C-1 与 I2S 输出。**（注：已移除多余的录音 ADC 引脚）**

| RPi 物理 PIN | BCM 引脚 | 音频板接口 | 详细功能描述说明 |
| :---: | :--- | :--- | :--- |
| **2 / 4** | 5V Power | **5V** | 音频板主供电驱动 |
| **6 / 9** | Ground | **GND** | 音频板主接地引脚 |
| **3** | BCM 2 (SDA1) | **SDA** | 硬件 I2C-1 数据线 (音频控制指令) |
| **5** | BCM 3 (SCL1) | **SCL** | 硬件 I2C-1 时钟线 (音频控制指令) |
| **12** | **BCM 18 (CLK)** | **CLK** | **I2S 位时钟 (音频核心，严禁屏幕抢占)** |
| **35** | BCM 19 (LRCK) | **LRCLK** | I2S 帧时钟 / 左右声道选择 |
| **40** | BCM 21 (DOUT) | **DAC** | I2S 放音数据输出线 (Data Output) |

### 2. SPI 彩色触摸屏 (SPI0 + 硬件 PWM1 + 软 I2C-3)
包含显示与触控数据链路，完美避开音频冲突。

| RPi 物理 PIN | BCM 引脚 | 屏幕端接口 | 详细功能描述说明 |
| :---: | :--- | :--- | :--- |
| **1** | 3.3V Power | **VCC / 3.3V**| 屏幕及触控主供电 |
| **39** | Ground | **GND** | 屏幕主接地引脚 |
| **19** | BCM 10 | **MOSI** | 硬件 SPI0 像素数据输出 |
| **21** | BCM 9 | **MISO** | 硬件 SPI0 数据输入 |
| **23** | BCM 11 | **SCLK** | 硬件 SPI0 时钟同步线 |
| **24** | BCM 8 | **CS** | 硬件 SPI0 片选使能引脚 |
| **22** | BCM 25 | **DC** | 屏幕数据 / 命令控制切换引脚 |
| **13** | BCM 27 | **RST** | 屏幕硬件复位引脚 |
| **33** | **BCM 13 (PWM1)**| **LCD_BL** | **屏幕背光控制 (硬件 PWM1 避让音频冲突)** |
| **7** | BCM 4 | **Touch SDA** | 软 I2C-3 总线数据线 (触控读取) |
| **29** | BCM 5 | **Touch SCL** | 软 I2C-3 总线时钟线 (触控读取) |
| **悬空** | N/A | **TP_INT** | **采用轮询架构，无需接线** |

---

## 💽 操作系统推荐

**推荐：Raspberry Pi OS Bookworm (64-bit) Lite 无头版本**

> 必须使用 **Raspberry Pi Imager** 预配置 WiFi 和 SSH 账户，不再支持修改 `wpa_supplicant.conf`。

---

## 📁 项目结构

```text
Ansible_RPI_TouchPlayer/
├── ansible/
│   ├── site.yml                 # 主 Playbook 入口
│   ├── inventory/
│   │   └── hosts.ini            # 目标主机清单与连接配置
│   ├── group_vars/
│   │   └── all.yml              # 全局变量配置 (I2C-3软引脚、音量限制等)
│   └── roles/                   # Ansible 角色模块
│       ├── system_base/         # 系统基础、时区与网络调优
│       ├── audio_core/          # PipeWire, WM8960 驱动与 三大音源服务
│       └── gui_touch/           # Python 绘图依赖、触控主循环部署
│
├── scripts/                     # Python 核心内存绘图与触控轮询代码
└── README.md                    # 本文档
```

---

## 🚀 部署流程

### 前置要求
- ✅ 本地控制端（电脑）已安装 **Ansible**。
- ✅ 树莓派已接入局域网，且可通过 SSH 免密登录。

### 快速开始

在 **本地电脑** (非树莓派) 执行：

```bash
# 1️⃣ 克隆仓库
git clone [https://github.com/holefrog/Ansible_RPI_TouchPlayer.git](https://github.com/holefrog/Ansible_RPI_TouchPlayer.git)
cd Ansible_RPI_TouchPlayer/ansible

# 2️⃣ 配置 Ansible 主机
cp inventory/hosts.ini.example inventory/hosts.ini
nano inventory/hosts.ini  # 填入树莓派的实际局域网 IP 和 用户名

# 3️⃣ 运行自动化部署
ansible-playbook -i inventory/hosts.ini site.yml
```

*Ansible 将全自动处理内核覆盖 (dtoverlay)、依赖安装、Python 环境构建及系统服务注册。多次执行依然安全（幂等性）。*

---

## 📊 日志与调试

部署完成后，如果需要调整横竖屏布局或触控热区，修改 `scripts/` 下的代码后，可通过以下命令追踪状态：

```bash
# 查看 UI 图形渲染刷新与触控坐标日志
journalctl -u touch_gui.service -f

# 检查 PipeWire 底层音频服务状态
journalctl -u pipewire.service -f
```

## 🤝 贡献与许可
- **许可证：** MIT License
- Made with ❤️ for the maker and audiophile community.