# 🎵 Ansible_RPI_TouchPlayer

将 Raspberry Pi 4B 打造为专业级多音源媒体播放器，支持 **Logitech Media Server (LMS)**、**AirPlay 2** 和 **蓝牙音频**，配备 **2.8 寸全彩触控屏**。本项目基于 **Ansible** 实现全自动化、幂等性部署，并采用“纯 Python 轻量化”图形交互架构。

---

## ✨ 核心特性

### 🎼 三音源无缝切换
- **🎹 Squeezelite** - 连接 Logitech Media Server，播放本地与流媒体音乐库
- **📱 AirPlay 2** - 从 iPhone/iPad/Mac 无缝推送音频 (基于 `shairport-sync`)
- **🔵 蓝牙音频** - 接收任何蓝牙设备的音频流 (支持自动配对与 A2DP)

### 🖥️ 极简触控交互 (纯 Python 轻量架构)
放弃沉重的系统级 GUI 框架，从底层榨取性能：
- 🚀 **高速推流**：`spidev` 配合 `Pillow` 内存绘图，`NumPy` 向量化极速转换 RGB565。
- 👆 **无感轮询**：摒弃硬件中断，使用 `smbus2` 对触控芯片 (软 I2C) 进行主循环同步轮询。
- 🎯 **盲操 UX 设计**：全屏切分为“左/中/右”三大隐形热区，彻底解决“胖手指”误触痛点。
- 💡 **硬件无闪调光**：屏幕背光直连备用硬件 PWM 通道，实现丝滑的智能屏保渐暗效果。

### 🔊 专业音频处理
- **PipeWire** - 采用现代音频服务器，取代老旧的 PulseAudio/ALSA 架构。
- **WM8960 声卡** - 独占标准 I2C 与 I2S 总线，提供高保真音频输出。

---

## 🛠️ 终极硬件接线指南 (严格区分信号流向)

为了让音频与显示系统完美共存，本项目进行了精密的硬件防冲突重构。
通信底层逻辑遵循严谨的主从架构视角：**树莓派 (RPi) 为主控 Host，音频板与屏幕为外设 Codec/Slave。**

### ⚠️ 核心防冲突设计必读
1. **音频时钟独占**：WM8960 必须独占 `BCM 18` 用于 I2S 位时钟传输。
2. **背光通道转移**：SPI 屏幕的默认背光引脚 (LCD_BL) 严禁接入 BCM 18，**必须飞线至备用硬件 PWM 通道 `BCM 13`**。
3. **触控总线隔离**：触控采用软件模拟的 `I2C-3`，与音频的硬件 `I2C-1` 彻底物理隔离，杜绝杂音。
4. **全双工驱动迎合**：WM8960 的录音输入线 (`BCM 20`) 虽不用于业务逻辑，但**予以保留**，以迎合底层 ALSA 驱动的全双工初始化自检，防止内核报错。

---

### 表 1：WM8960 音频板 (I2C-1 控制 + I2S 数据)
作为核心发声单元，独占硬件音频总线。

| RPi 物理引脚 (BCM) | RPi 端功能 (主控视角) | 信号绝对流向 | 外设端接口 | 外设端功能 (WM8960 视角) |
| :---: | :--- | :---: | :--- | :--- |
| **2 或 4** | 5V 电源输出 | **➔ 供电 ➔** | **5V** | 接收 5V 功放主供电 |
| **6 或 9** | GND 接地 | **➖ 共地 ➖** | **GND** | 模块共地 |
| **3** (BCM 2) | I2C-1 SDA (数据) | **⬌ 双向 ⬌** | **SDA** | 接收/发送音频初始化控制指令 |
| **5** (BCM 3) | I2C-1 SCL (时钟) | **➔ 输出 ➔** | **SCL** | 接收 I2C 时钟同步信号 |
| **12** (BCM 18)| I2S CLK (位时钟) | **➔ 输出 ➔** | **CLK** | 接收 I2S 硬件位时钟 (**严禁抢占**) |
| **35** (BCM 19)| I2S LRCLK (帧时钟)| **➔ 输出 ➔** | **LRCLK** | 接收左右声道音频帧切换信号 |
| **40** (BCM 21)| I2S DOUT (播放) | **➔ 输出 ➔** | **DAC** (RXSDA) | **接收**数字音频流，解码并驱动喇叭发声 |
| **38** (BCM 20)| I2S DIN (录音) | **⬅ 输入 ⬅** | **ADC** (TXSDA) | **发送**麦克风采集的数字流 (满足驱动双工自检) |

---

### 表 2：2.8 寸 SPI 彩色触摸屏 (SPI0 + 硬件 PWM1 + 软 I2C-3)
包含 ST7789 画面渲染与 FT6336U 触控读取，已避开所有硬件冲突点。

| RPi 物理引脚 (BCM) | RPi 端功能 (主控视角) | 信号绝对流向 | 外设端接口 | 外设端功能 (屏幕/触控视角) |
| :---: | :--- | :---: | :--- | :--- |
| **1** | 3.3V 电源输出 | **➔ 供电 ➔** | **VCC** (3.3V) | 接收 3.3V 逻辑与屏幕供电 |
| **39** | GND 接地 | **➖ 共地 ➖** | **GND** | 模块共地 |
| **19** (BCM 10)| SPI0 MOSI (发送数据)| **➔ 输出 ➔** | **MOSI** | 接收 SPI 高速像素点阵画面数据 |
| **21** (BCM 9) | SPI0 MISO (接收数据)| **⬅ 输入 ⬅** | **MISO** | 发送 SPI 硬件状态数据 (可选) |
| **23** (BCM 11)| SPI0 SCLK (SPI时钟)| **➔ 输出 ➔** | **SCLK** | 接收 SPI 高频时钟同步信号 |
| **24** (BCM 8) | SPI0 CE0 (片选使能)| **➔ 输出 ➔** | **CS** | 接收 SPI 通信激活信号 |
| **22** (BCM 25)| GPIO (数据/命令切换)| **➔ 输出 ➔** | **DC** | 区分当前收到的是像素数据还是控制命令 |
| **13** (BCM 27)| GPIO (硬件复位) | **➔ 输出 ➔** | **RST** | 接收屏幕硬件初始化复位信号 |
| **33** (BCM 13)| PWM1 (硬件脉宽调制)| **➔ 输出 ➔** | **LCD_BL** | 接收调光信号 (**转移至 BCM 13 完美避开冲突**) |
| **7** (BCM 4) | 软 I2C-3 SDA (数据)| **⬌ 双向 ⬌** | **Touch SDA**| 发送/接收 FT6336U 触控坐标数据 |
| **29** (BCM 5) | 软 I2C-3 SCL (时钟)| **➔ 输出 ➔** | **Touch SCL**| 接收触控 I2C 时钟同步信号 |
| **悬空不接** | 纯轮询模式无需中断 | **❌ 断开 ❌** | **TP_INT** | 触控中断输出引脚 (**精简架构，悬空**) |

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
│       ├── audio_core/          # PipeWire, WM8960 驱动与三大音源服务
│       └── gui_touch/           # Python 绘图依赖、触控主循环服务部署
│
├── scripts/                     # Python 核心内存绘图与触控轮询代码
└── README.md                    # 本文档
```

---

## 🚀 部署流程

### 前置要求
- ✅ 目标系统：**Raspberry Pi OS Bookworm (64-bit) Lite** 无头版本 (使用 RPi Imager 预配 WiFi 与 SSH)。
- ✅ 本地控制端（电脑）已安装 **Ansible**。

### 快速开始 (在电脑端执行)

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

---

## 📊 日志与调试

部署完成后，如果需要调整横竖屏 UI 布局或触控热区，直接修改 `scripts/` 下的 Python 源码。可通过以下命令追踪系统运行状态：

```bash
# 查看 UI 图形渲染刷新与触控坐标日志
journalctl -u touch_gui.service -f

# 检查 PipeWire 底层音频服务器及设备挂载状态
journalctl -u pipewire.service -f
```

## 🤝 贡献与许可
- **许可证：** MIT License
- Made with ❤️ for the maker and audiophile community.