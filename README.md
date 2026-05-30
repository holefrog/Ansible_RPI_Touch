好的，为您重新整合并生成了最终满血版的 `README.md`。这里将之前讨论的所有核心特性、完整的硬件接线对照表（音频+屏幕总表）、冲突规避方案以及自动化部署步骤全部收录其中。

你可以直接点击代码块右上角的“复制”按钮，无损粘贴到你的项目中。

```markdown
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

## 🛠️ 全硬件详细接线图总表 (Hardware Wiring Guide)

为了让系统能够完美共存，本项目经过精密的硬件重构，彻底解决了 **WM8960 音频板** 与 **SPI 触摸屏** 之间的所有潜在物理冲突。

### ⚠️ 三大核心防冲突设计说明
1. **背光冲突避让**：SPI 屏幕出厂默认的背光引脚 (LCD_BL) 通常占用 BCM 18，但该引脚已被 WM8960 的 I2S CLK 独占。**必须将屏幕背光引脚单独飞线至 BCM 13 (物理引脚 33)**。
2. **触控总线隔离**：FT6336U 触控芯片使用 GPIO 模拟的 **I2C-3** 独立通道，与音频控制的标准 I2C-1 在物理上完全隔离，杜绝高频触摸对音频数据产生杂音干扰。
3. **中断引脚悬空**：系统软件架构采用高效的主循环同步轮询模式，因此**触摸中断引脚 (TP_INT) 无需连接**，精简了接线复杂度。

### 📋 树莓派 4B 与各组件 1对1 物理接线图

| 树莓派物理 PIN | 树莓派 BCM 引脚 | 组件端接口名称 | 组件归属分类 | 详细功能描述说明 |
| :---: | :--- | :--- | :--- | :--- |
| **1** | 3.3V Power | **VCC / 3.3V** | SPI 触摸屏 | 屏幕控制及触摸芯片主供电 |
| **2 / 4** | 5V Power | **5V** | WM8960 音频板 | 音频板主供电驱动 |
| **3** | BCM 2 (SDA1) | **SDA** | WM8960 音频板 | 硬件 I2C-1 总线数据线 (音频控制) |
| **5** | BCM 3 (SCL1) | **SCL** | WM8960 音频板 | 硬件 I2C-1 总线时钟线 (音频控制) |
| **6 / 9** | Ground | **GND** | WM8960 音频板 | 音频板主接地引脚 |
| **7** | BCM 4 | **Touch SDA** | SPI 触摸屏 | 模拟 I2C-3 总线数据线 (触控数据读取) |
| **12** | **BCM 18 (CLK)** | **CLK** | WM8960 音频板 | **I2S 位时钟 (Bit Clock) - 音频核心，严禁抢占** |
| **13** | BCM 27 | **RST** | SPI 触摸屏 | 屏幕硬件复位引脚 |
| **19** | BCM 10 (MOSI) | **MOSI** | SPI 触摸屏 | 标准硬件 SPI0 主输出从输入像素数据 |
| **21** | BCM 9 (MISO) | **MISO** | SPI 触摸屏 | 标准硬件 SPI0 主输入从输出数据 |
| **22** | BCM 25 | **DC** | SPI 触摸屏 | 屏幕数据 / 命令控制切换引脚 (Data/Command) |
| **23** | BCM 11 (SCLK) | **SCLK** | SPI 触摸屏 | 标准硬件 SPI0 时钟同步线 |
| **24** | BCM 8 (CE0) | **CS** | SPI 触摸屏 | 标准硬件 SPI0 片选使能引脚 |
| **29** | BCM 5 | **Touch SCL** | SPI 触摸屏 | 模拟 I2C-3 总线时钟线 (触控数据读取) |
| **33** | **BCM 13 (PWM1)**| **LCD_BL** | SPI 触摸屏 | **屏幕背光控制 - 使用硬件 PWM1 通道完美避让音频冲突** |
| **35** | BCM 19 (LRCK) | **LRCLK** | WM8960 音频板 | I2S 帧时钟 / 左右声道选择 (Frame Clock) |
| **38** | BCM 20 (DIN) | **ADC** | WM8960 音频板 | I2S 录音数据输入线 (Data Input) |
| **39** | Ground | **GND** | SPI 触摸屏 | 屏幕主接地引脚 |
| **40** | BCM 21 (DOUT) | **DAC** | WM8960 音频板 | I2S 放音数据输出线 (Data Output) |
| **悬空** | N/A | **TP_INT** | SPI 触摸屏 | 触摸中断引脚 - **采用同步轮询架构，故无需接线** |

---

## 📁 项目架构 (Ansible Roles)

```text
Ansible_RPI_TouchPlayer/
├── ansible/
│   ├── group_vars/
│   │   └── all.yml             # 全局配置 (如音量限制、I2C-3 软引脚定义)
│   ├── roles/
│   │   ├── system_base/        # 基础环境、系统时区、内核优化、网络调优
│   │   ├── audio_core/         # PipeWire 底座, WM8960 驱动覆盖, 三大音源服务部署
│   │   └── gui_touch/          # Python 虚拟环境构建, NumPy/Pillow 依赖安装, 部署主循环及 systemd 服务
│   ├── site.yml                # 主控 Playbook
│   └── hosts.ini               # 目标主机清单
├── scripts/                    # Python 核心内存绘图与 Touch 轮询控制主循环代码
└── README.md                   # 本说明文件
```

---

## 🚀 自动化一键部署

### 1. 前置要求
* 目标树莓派已安装 **Raspberry Pi OS Bookworm (64-bit) Lite** 原生无头版本。
* 本地控制端电脑已安装 `ansible`。
* 树莓派已接入局域网，且控制端可通过 SSH 免密（Public Key）登录。

### 2. 快速部署
在你的**本地控制端电脑** (非树莓派本地) 执行：

```bash
# 克隆本仓库
git clone [https://github.com/holefrog/Ansible_RPI_TouchPlayer.git](https://github.com/holefrog/Ansible_RPI_TouchPlayer.git)
cd Ansible_RPI_TouchPlayer/ansible

# 拷贝并修改主机配置
cp hosts.ini.example hosts.ini
nano hosts.ini  # 填入你树莓派的实际局域网 IP 地址

# 一键运行部署
ansible-playbook -i hosts.ini site.yml
```

*Ansible 将全自动处理内核配置覆盖 (dtoverlay 软 I2C 定义)、系统底层音频服务重构、Python 运行环境构建及守护进程开机自启。多次执行依然安全（符合幂等性原则）。*

---

## 🛠 开发与调试指南

如果你需要调整 UI 的横竖屏布局、字体样式或优化触控碰撞热区，只需修改 `scripts/` 目录下的核心 Python 脚本。部署完成后，可以使用以下命令在树莓派上实时追踪系统运行状态：

```bash
# 查看 UI 图形渲染刷新与触控坐标轮询日志
journalctl -u touch_gui.service -f

# 检查 PipeWire 音频服务器及音源流状态
journalctl -u pipewire.service -f
```

## 🤝 贡献与许可
* **许可证：** MIT License
* Made with ❤️ for the maker and audiophile community.

```