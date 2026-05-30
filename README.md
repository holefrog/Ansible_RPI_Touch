# 🎵 Ansible_RPI_TouchPlayer

本项目致力于将 Raspberry Pi 4B 打造为一个支持多音源无缝切换的**专业级纯净媒体播放器**。
通过彻底的硬件逻辑重构，本作从传统的单色 OLED 升级为 **2.8/3.5 寸全彩 SPI 电容触摸屏**，并基于纯 Python 与 `smbus2` 轮询架构，实现了全屏隐形热区的“盲操”级触控交互。

整个系统架构采用 **Ansible 全自动化幂等部署**，彻底告别繁杂的 Linux 命令行配置。

---

## ✨ 核心特性

### 🎼 多音源无缝路由 (基于 PipeWire)
* **🎹 Squeezelite** - 连接 Logitech Media Server，播放无损本地音乐库。
* **📱 AirPlay 2** - 从 iPhone/iPad/Mac 推送系统级音频。
* **🔵 Bluetooth A2DP** - 接收任何蓝牙设备的音频流。

### 🖥️ 纯 Python 轻量化触控 UI
* **极速推屏**：完全摒弃沉重的系统 GUI 框架，采用 `Pillow` 内存绘图 + `NumPy` 向量化转码 (RGB565 大端序) + `spidev.writebytes2` 零拷贝 DMA 直推。
* **隐形热区盲操**：抛弃传统微小按钮，将屏幕划分为大型触控区块（左/中/右），完美解决小屏幕的“胖手指”误触问题。
* **物理防冲突调光**：转移默认背光引脚至 BCM 13 (硬件 PWM1)，实现丝滑的呼吸级暗屏、息屏，且**绝对不干扰音频底层时钟**。

### 🔊 硬件级发声底座
* 采用 **Waveshare WM8960 Sound Board** 提供高保真 I2S 硬件解码输出。
* 独立音量控制与优先级自动管理。

---

## 🧩 核心硬件接线指南 (Pinout Guide)

> **⚠️ 架构警告 (冲突规避)**
> 本项目同时挂载了 SPI 触摸屏与 I2S 音频板。**绝对不能**按照屏幕官方维基的默认方式连接！请严格遵循以下两张接线表，我们已从物理层和软件层彻底解决了总线冲突。

### 1. WM8960 音频板 (独占硬 I2C-1 与 I2S)
作为核心发声单元，音频板保持独占树莓派的标准音频与控制总线。
*(注：保留 38 脚录音数据线是为了满足 Linux ALSA 驱动的全双工初始化自检，防止底层报错)*

| 树莓派主控端 (RPi 4B) | 绝对数据流向 | WM8960 音频板 (外设端) | 功能说明 |
| :--- | :---: | :--- | :--- |
| **PIN 2 或 4** (5V) | `➔ 供电 ➔` | **5V** | 5V 主供电 |
| **PIN 6 或 9** (GND) | `➔ 接地 ➔` | **GND** | 统一接地 |
| **PIN 3** (BCM 2) | `↔ 双向 ↔` | **SDA** | I2C-1 音频控制数据 |
| **PIN 5** (BCM 3) | `➔ 发送 ➔` | **SCL** | I2C-1 音频控制时钟 |
| **PIN 12** (BCM 18) | `➔ 发送 ➔` | **CLK** | I2S 位时钟 (极其敏感，切勿被抢占) |
| **PIN 35** (BCM 19) | `➔ 发送 ➔` | **LRCLK (WS)** | I2S 左右声道帧时钟 |
| **PIN 40** (BCM 21) | `➔ 发送 ➔` | **DAC (RXSDA)** | **播放：** 将树莓派的数字音频推给声卡发声 |
| **PIN 38** (BCM 20) | `⬅ 接收 ⬅` | **ADC (TXSDA)** | **录音：** 声卡麦克风数据发给树莓派 (迎合驱动自检) |

### 2. SPI 彩色电容触摸屏 (SPI0 + 软 I2C-3 + PWM1)
显示采用标准 SPI 推流，触控采用 GPIO 模拟的独立 I2C-3 总线（完全物理隔离音频总线），同时采用**纯轮询模式**放弃中断引脚。

| 树莓派主控端 (RPi 4B) | 绝对数据流向 | 触摸屏端 (ST7789/96S + FT6336U) | 功能说明 |
| :--- | :---: | :--- | :--- |
| **PIN 1** (3.3V) | `➔ 供电 ➔` | **VCC / 3.3V** | 屏幕及触控芯片主供电 |
| **PIN 39** (GND) | `➔ 接地 ➔` | **GND** | 统一接地 |
| **PIN 19** (BCM 10) | `➔ 发送 ➔` | **MOSI** | SPI0 传输像素数据至屏幕 |
| **PIN 21** (BCM 9) | `⬅ 接收 ⬅` | **MISO** | SPI0 屏幕数据返回 (可选) |
| **PIN 23** (BCM 11) | `➔ 发送 ➔` | **SCLK** | SPI0 传输时钟 |
| **PIN 24** (BCM 8) | `➔ 发送 ➔` | **CS** | SPI0 硬件片选 |
| **PIN 22** (BCM 25) | `➔ 发送 ➔` | **DC (Data/Cmd)** | 屏幕数据/命令切换引脚 |
| **PIN 13** (BCM 27) | `➔ 发送 ➔` | **LCD_RST / RST** | 屏幕显示芯片复位 |
| **PIN 11** (BCM 17) | `➔ 发送 ➔` | **TP_RST** | ✅ **触控芯片复位** (必需的初始化信号) |
| **PIN 33** (BCM 13) | `➔ 发送 ➔` | **LCD_BL / BL** | 🚨 **背光控制：** 转移至 PWM1 通道，避开 BCM18 音频冲突 |
| **PIN 7** (BCM 4) | `↔ 双向 ↔` | **TP_SDA** | 软 I2C-3 触控数据线 (由 dtoverlay 驱动) |
| **PIN 29** (BCM 5) | `➔ 发送 ➔` | **TP_SCL** | 软 I2C-3 触控时钟线 |
| **未连接 (NC)** | `N/A` | **TP_INT** | ❌ **触控中断：** 采用纯 Python 轮询模式，无需连接此针脚 |

---

## 🚀 自动化部署流程 (Ansible)

本项目的所有底层依赖、服务注册、以及复杂的 `dtoverlay` (软 I2C 开启、SPI 提速等) 均由 Ansible 一键接管。

### 1. 前置要求
* 目标树莓派已安装 **Raspberry Pi OS Bookworm (64-bit) Lite** 无头版本。
* 树莓派已接入网络，且可通过 SSH 免密登录。
* 你的本地控制端电脑（Mac/Linux）已安装 `ansible`。

### 2. 快速开始
在你的**本地电脑**终端执行：

```bash
# 1. 克隆项目
git clone [https://github.com/your-username/Ansible_RPI_TouchPlayer.git](https://github.com/your-username/Ansible_RPI_TouchPlayer.git)
cd Ansible_RPI_TouchPlayer/ansible

# 2. 复制并编辑 hosts 文件，填入你的树莓派 IP
cp hosts.ini.example hosts.ini
nano hosts.ini

# 3. 一键执行自动化部署
ansible-playbook -i hosts.ini site.yml
```
*(注：部署过程中若修改了底层的硬件 boot 配置，Ansible 会自动重启树莓派，属于正常现象。)*

---

## 🛠 开发与调试

如果需要调整屏幕 UI 布局、字体大小或触控的“隐形热区”碰撞边界，只需修改 `scripts/` 目录下的 Python 核心文件，无需重新跑整个 Playbook。

你可以通过以下命令在树莓派上实时查看 UI 与触控服务的日志：
```bash
sudo journalctl -u touch_gui.service -f
```

## 🤝 贡献与许可
* **许可证**： MIT License - 欢迎自由改造、分发。
* Made with ❤️ for the Maker Community.