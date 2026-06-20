[🇺🇸 English](README.md) | [🇨🇳 中文](README_zh-CN.md)

# 🎵 Ansible_RPI_TouchPlayer

本项目致力于将 Raspberry Pi 4B 打造为一个支持多音源无缝切换的**专业级纯净媒体播放器**。
通过彻底的硬件逻辑重构，本作从传统的单色 OLED 升级为 **3.5 寸全彩 SPI 电容触摸屏**，并基于纯 Python 与 `smbus2` 轮询架构，实现了全屏隐形热区的"盲操"级触控交互。

整个系统架构采用 **Ansible 全自动化幂等部署**，彻底告别繁杂的 Linux 命令行配置。

---

## 📑 目录 (Table of Contents)

- [🖼️ UI 预览 (Interface Gallery)](#-ui-预览-interface-gallery)
  - [🎼 多音源无缝切换 (Audio Sources)](#-多音源无缝切换-audio-sources)
  - [🎛️ 触控交互与遮罩 (Interactive Overlays)](#-触控交互与遮罩-interactive-overlays)
  - [📻 待机与信息屏 (Standby & Info)](#-待机与信息屏-standby--info)
- [✨ 核心特性](#-核心特性)
  - [🎼 多音源无缝路由 (基于 PipeWire)](#-多音源无缝路由-基于-pipewire)
  - [🖥️ 高性能触控 UI](#-高性能触控-ui)
  - [🔊 硬件级发声底座](#-硬件级发声底座)
- [🧩 硬件装配指南 (Hardware Guide)](#-硬件装配指南-hardware-guide)
  - [🧩 核心硬件接线指南 (Pinout Guide)](#-核心硬件接线指南-pinout-guide)
    - [1. WM8960 音频板 (独占硬 I2C-1 与 I2S)](#1-wm8960-音频板-独占硬-i2c-1-与-i2s)
    - [2. SPI 彩色电容触摸屏 (SPI0 + 硬件 I2C-3 + PWM1)](#2-spi-彩色电容触摸屏-spi0--硬件-i2c-3--pwm1)
  - [🌟 树莓派屏幕背光闪烁彻底解决与硬件 PWM 配置指南](#-树莓派屏幕背光闪烁彻底解决与硬件-pwm-配置指南)
    - [1. 为什么背光会闪烁？](#1-为什么背光会闪烁)
    - [2. 如何开启硬件 PWM (以 BCM 13 引脚为例)](#2-如何开启硬件-pwm-以-bcm-13-引脚为例)
    - [3. 验证硬件 PWM 状态](#3-验证硬件-pwm-状态)
    - [4. 软件层驱动](#4-软件层驱动)
- [🚀 安装与部署 (Installation & Deployment)](#-安装与部署-installation--deployment)
  - [🚀 自动化部署流程 (Ansible)](#-自动化部署流程-ansible)
    - [🎭 Ansible Role 分工 (Role Responsibilities)](#-ansible-role-分工-role-responsibilities)
    - [1. 前置要求](#1-前置要求)
    - [2. 快速开始](#2-快速开始)
  - [关于禁用系统自动更新的说明](#关于禁用系统自动更新的说明)
  - [📦 Python 依赖管理策略：混合优雅模式 (Hybrid Elegance)](#-python-依赖管理策略混合优雅模式-hybrid-elegance)
    - [⚙️ 为什么这样设计？](#-为什么这样设计)
    - [1. 底层硬件与 C 扩展库使用 `apt` 管理](#1-底层硬件与-c-扩展库使用-apt-管理)
    - [2. 纯 Python 业务逻辑库使用 `pip` (venv) 管理](#2-纯-python-业务逻辑库使用-pip-venv-管理)
    - [🛠️ Ansible 部署实现](#-ansible-部署实现)
  - [📦 手动安装依赖与运行指南 (Manual Setup & Dependencies)](#-手动安装依赖与运行指南-manual-setup--dependencies)
    - [1. 开启 SPI 和 I2C 接口](#1-开启-spi-和-i2c-接口)
    - [2. 安装 Python 系统级依赖](#2-安装-python-系统级依赖)
    - [3. 运行 Demo](#3-运行-demo)
    - [🛠️ 为适配 RPi 4B/Trixie 所做的核心修改](#-为适配-rpi-4btrixie-所做的核心修改)
- [🧑‍💻 开发调试与架构决策 (Development & Architecture)](#-开发调试与架构决策-development--architecture)
  - [🛠 开发与调试](#-开发与调试)
    - [📸 极客截屏指南](#-极客截屏指南)
  - [🏗️ 架构演进与性能极致优化](#-架构演进与性能极致优化)
    - [1. 突破物理极限的"脏区渲染" (Dirty Rectangle)](#1-突破物理极限的脏区渲染-dirty-rectangle)
    - [2. 告别上帝对象：模块化大拆分](#2-告别上帝对象模块化大拆分)
    - [3. 彻底分离配置边界](#3-彻底分离配置边界)
    - [4. 交互升华：零延迟进度条拖拽](#4-交互升华零延迟进度条拖拽)
    - [⚡ 树莓派 SPI 屏幕驱动图像处理与传输优化总结](#-树莓派-spi-屏幕驱动图像处理与传输优化总结)
    - [1. 核心优化：彻底消除 Python 列表转换开销](#1-核心优化彻底消除-python-列表转换开销)
    - [2. 算法优化：Numpy 向量化位运算 (RGB888 转 RGB565)](#2-算法优化numpy-向量化位运算-rgb888-转-rgb565)
    - [3. 内存优化：对象复用与降低 GC 压力](#3-内存优化对象复用与降低-gc-压力)
    - [4. 架构优化：剥离高频轮询线程](#4-架构优化剥离高频轮询线程)
    - [🎞️ 图像撕裂问题与滚动优化 (Screen Tearing & Scrolling Optimization)](#-图像撕裂问题与滚动优化-screen-tearing--scrolling-optimization)
    - [遇到的问题 (Problem)](#遇到的问题-problem)
    - [解决方法与最终方案 (Solution)](#解决方法与最终方案-solution)
    - [🏛️ UI 架构决策记录 (Architecture Decision Record)](#-ui-架构决策记录-architecture-decision-record)
    - [背景](#背景)
    - [决策：精准重构，拒绝过度设计](#决策精准重构拒绝过度设计)
    - [实际执行的三项精准改动](#实际执行的三项精准改动)
    - [1. 浮层状态改为枚举互斥变量](#1-浮层状态改为枚举互斥变量)
    - [2. 进度条拖拽状态合并](#2-进度条拖拽状态合并)
    - [3. 删除 render_key 机制](#3-删除-render_key-机制)
    - [4. 音量条交互简化](#4-音量条交互简化)
- [🤝 贡献与许可](#-贡献与许可)

---


## 🖼️ UI 预览 (Interface Gallery)

### 🎼 多音源无缝切换 (Audio Sources)
<p align="center">
  <img src="UI/Src-Airplay.png" width="32%" alt="AirPlay" />
  <img src="UI/Src-Bluetooth-1.png" width="32%" alt="Bluetooth" />
  <img src="UI/Src_Squeeze-LMS.png" width="32%" alt="Squeezelite" />
</p>

### 🎛️ 触控交互与遮罩 (Interactive Overlays)
<p align="center">
  <img src="UI/Main-Volume.png" width="32%" alt="Volume Overlay" />
  <img src="UI/Main-mask.png" width="32%" alt="Action Mask" />
  <img src="UI/Src-Bluetooth-2.png" width="32%" alt="Bluetooth Menu" />
</p>

### 📻 待机与信息屏 (Standby & Info)
<p align="center">
  <img src="UI/Screensaver.png" width="32%" alt="Nixie Tube Screensaver" />
  <img src="UI/Photo-Screen.png" width="32%" alt="Photo Frame" />
  <img src="UI/Info.png" width="32%" alt="System Info" />
</p>

---

## ✨ 核心特性

### 🎼 多音源无缝路由 (基于 PipeWire)
* **🎹 Squeezelite** - 连接 Logitech Media Server，播放无损本地音乐库。
* **📱 AirPlay 2** - 从 iPhone/iPad/Mac 推送系统级音频。
* **🔵 Bluetooth A2DP** - 接收任何蓝牙设备的音频流。

### 🖥️ 高性能触控 UI
* **全屏触控界面**：为 480x320 屏幕设计明确的触控区域与状态反馈，提升操作直观性与延迟表现。
* **硬 I2C + SPI 硬件隔离**：将触摸控制与屏幕刷新分别通过硬件 I2C-3 与 SPI 传输，保持与 WM8960 音频总线的物理隔离，且不占用额外 CPU 资源。

### 🔊 硬件级发声底座
* 采用 **Waveshare WM8960 Sound Board** 提供高保真 I2S 硬件解码输出。
  > **💡 独家驱动优化**：由于官方只为双麦克风版 (12.288MHz) 的 HAT 提供了 Linux 驱动，导致单麦克风版 (24MHz) 的 Audio Board 在树莓派上录音时会产生时钟错位与纯白噪声。我们针对此 24MHz 单麦克风版本的硬件，彻底修复并生成了专属的底层 Linux 驱动 `wm8960-audio-card.dtbo`，并内置在了 Ansible 中实现**全自动无感部署**与音频路由配置。详细的排查历程与技术细节请见 [RECORD.md](documents/WM8960/RECORD.md)。
* 独立音量控制与优先级自动管理。

---

---

## 🧩 硬件装配指南 (Hardware Guide)

### 🧩 核心硬件接线指南 (Pinout Guide)

> **⚠️ 架构警告 (冲突规避)**
> 本项目同时挂载了 SPI 触摸屏与 I2S 音频板。**绝对不能**按照屏幕官方维基的默认方式连接！请严格遵循以下两张接线表，我们已从物理层和软件层彻底解决了总线冲突。

#### 1. WM8960 音频板 (独占硬 I2C-1 与 I2S)
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

#### 2. SPI 彩色电容触摸屏 (SPI0 + 硬件 I2C-3 + PWM1)
产品资料: [https://www.waveshare.net/wiki/3.5inch_Capacitive_Touch_LCD?hl=zh-CN]

显示采用标准 SPI 推流，触控采用树莓派 4B 原生的独立硬件 I2C-3 总线（完全物理隔离音频总线），同时采用**纯轮询模式**放弃中断引脚。

| LCD引脚号 | LCD引脚 | 树莓派物理引脚 | 树莓派(BCM) | 功能说明 |
| :---: | :--- | :--- | :--- | :--- |
| 1 | VCC | PIN 2 | 5V | 屏幕及触控芯片主供电 (5V) |
| 2 | 3V3 | NC | NC | 悬空不接 (已使用5V供电) |
| 3 | GND | PIN 6 | GND | 统一接地 |
| 4 | MISO | PIN 21 | BCM 9 | SPI0 屏幕数据返回 (可选) |
| 5 | MOSI | PIN 19 | BCM 10 | SPI0 传输像素数据至屏幕 |
| 6 | SCLK | PIN 23 | BCM 11 | SPI0 传输时钟 |
| 7 | SD_CS | NC | NC | SD 卡片选 (未使用) |
| 8 | LCD_CS | PIN 24 | BCM 8 | SPI0 硬件片选 |
| 9 | LCD_DC | PIN 22 | BCM 25 | 屏幕数据/命令切换引脚 |
| 10 | LCD_RST | PIN 13 | BCM 27 | 屏幕显示芯片复位 |
| 11 | LCD_BL | PIN 33 | BCM 13 | 屏幕背光控制 (PWM1，避开 I2S CLK) |
| 12 | TP_SDA | PIN 7 | BCM 4 | 硬件 I2C-3 触控数据线 (原生硬件控制器) |
| 13 | TP_SCL | PIN 29 | BCM 5 | 硬件 I2C-3 触控时钟线 (原生硬件控制器) |
| 14 | TP_INT | NC | NC | ❌ **触控中断：** 采用纯轮询模式，悬空不接 |
| 15 | TP_RST | PIN 11 | BCM 17 | ✅ **触控芯片复位** (必需的初始化信号) |

---

### 🌟 树莓派屏幕背光闪烁彻底解决与硬件 PWM 配置指南

#### 1. 为什么背光会闪烁？

软件 PWM 依赖 CPU 线程调度模拟方波，在系统负载突增时会发生毫秒级调度延迟，在低占空比下（< 5%）导致整个高电平脉冲被"吞掉"，产生明显闪烁。

**终极解决方案**：启用树莓派原生的**硬件定时器芯片 (Hardware PWM)** 接管背光引脚。

#### 2. 如何开启硬件 PWM (以 BCM 13 引脚为例)

编辑 `/boot/firmware/config.txt`：

```ini
# Enable PWM for Backlight Control on BCM 13
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
```

> **⚠️ BCM 12 与 BCM 13 双通道绑定**：`pwm-2chan` 会同时强制重置 BCM 12 和 BCM 13 的引脚模式。如果 BCM 12 已被其他外设（如 I2S 数据线）占用，此指令会导致其瘫痪。

#### 3. 验证硬件 PWM 状态

```bash
ls -l /sys/class/pwm/        # 期望看到 pwmchip0
pinctrl get 13               # 期望看到 a0 和 PWM 字样
```

#### 4. 软件层驱动

通过 Linux 原生 `sysfs` 接口控制，避免 GPIO 库篡改引脚模式：

    ```yaml
    # ansible/roles/system/tasks/hw_wm8960.yml 部分节选
    - name: Compile WM8960 Audio Card overlay
      ansible.builtin.command:
        cmd: dtc -@ -I dts -O dtb -o /boot/firmware/overlays/wm8960-audio-card.dtbo /tmp/wm8960-audio-card.dts
      
    - name: Configure WM8960 amixer settings
      ansible.builtin.shell: |
        amixer -c wm8960audiocard cset name='Left Boost Mixer LINPUT1 Switch' on
        amixer -c wm8960audiocard cset name='Capture Switch' on
        amixer -c wm8960audiocard cset name='ADC Data Output Select' 1
    ```   > /sys/class/pwm/pwmchip0/pwm1/enable

---

---

## 🚀 安装与部署 (Installation & Deployment)

### 🚀 自动化部署流程 (Ansible)

本项目的所有底层依赖、服务注册、以及复杂的 `dtoverlay` (硬 I2C 开启、SPI 提速等) 均由 Ansible 一键接管。

#### 🎭 Ansible Role 分工 (Role Responsibilities)
基于松耦合和职责分明的原则，本项目的 Ansible Roles 进行了严格的功能解耦：
* **`system`**: **(核心基座)** 负责所有系统级别的全局设置与底层硬件隔离。管理系统包更新、环境配置，并**集中管理所有底层硬件接口**（包括开启 I2C、SPI，挂载音频板和触摸屏的 dtoverlay）。所有硬件级重启（Reboot）均由此角色统筹判断。
* **`touchscreen`**: 负责基于 Python 的微雪 SPI 屏幕驱动及界面的应用级部署。由于底层硬件总线已在 `system` 中开启配置，该角色纯粹专注于源码传输以及注册运行 Systemd UI 服务。
* **`bluetooth` / `airplay` / `squeezelite`**: 各自独立负责对应的音频流接收服务的软件层安装、配置和 Systemd 守护进程管理。
* **`pipewire` / `volume`**: 负责底层的核心音频路由引擎搭建以及多路音量的混音控制逻辑。

#### 1. 前置要求
* 目标树莓派已安装 **Raspberry Pi OS Trixie (64-bit) Lite** 无头版本。
* 你的本地控制端电脑（Mac/Linux）已安装 `ansible`。
* **树莓派已接入网络，且配置了 SSH 免密登录**。具体配置步骤如下：
  1. 测试使用密码 SSH 登录到树莓派：
     ```bash
     ssh <你的用户名>@<你的树莓派IP>
     ```
  2. 在本地电脑生成 SSH 密钥（如果尚未生成）：
     ```bash
     ssh-keygen -t rsa -b 4096
     ```
  3. 将本地公钥复制到树莓派（使用 `ssh-copy-id` 或 `scp`）：
     ```bash
     # 推荐使用 ssh-copy-id 一键配置：
     ssh-copy-id <你的用户名>@<你的树莓派IP>

     # 或者使用 scp 手动复制并配置：
     scp ~/.ssh/id_rsa.pub <你的用户名>@<你的树莓派IP>:~/
     ssh <你的用户名>@<你的树莓派IP> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat ~/id_rsa.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && rm ~/id_rsa.pub"
     ```
  4. 再次执行 `ssh <你的用户名>@<你的树莓派IP>`，确认能够免密直接登录。

#### 2. 快速开始
在你的**本地电脑**终端执行：

```bash
# 1. 克隆项目
git clone https://github.com/your-username/Ansible_RPI_TouchPlayer.git
cd Ansible_RPI_TouchPlayer/ansible

# 2. 复制并编辑 hosts 文件，填入你的树莓派 IP
cp hosts.ini.example hosts.ini
nano hosts.ini

# 3. 一键执行自动化部署
ansible-playbook -i hosts.ini site.yml
```
*(注：部署过程中若修改了底层的硬件 boot 配置，Ansible 会自动重启树莓派，属于正常现象。)*

---

### 关于禁用系统自动更新的说明

在部署过程中，Ansible 剧本会自动卸载 `unattended-upgrades` 包以禁用操作系统的自动更新，原因如下：

1. **保障系统稳定性**：本设备依赖特定的硬件接口（SPI驱动）以及硬件交互程序。Linux 内核或底层驱动如果发生后台自动升级，极易破坏依赖项，导致自编界面或触摸屏失效。
2. **确保播放体验流畅**：后台自动下载和安装更新会抢占 CPU、内存和磁盘 I/O 资源，可能造成媒体播放卡顿、掉帧，甚至在核心组件更新后引发系统强制重启，直接中断当前的播放任务。
3. **延长 SD 卡寿命**：频繁的后台 APT 缓存更新和软件包写入会大幅增加对存储介质的写入次数，这会显著加速 MicroSD 卡的物理磨损。

---

### 📦 Python 依赖管理策略：混合优雅模式 (Hybrid Elegance)

本项目运行在现代化的树莓派系统环境（如 Debian 13 Trixie, Linux Kernel 6.12+）上。该环境默认启用了 **PEP 668 (EXTERNALLY-MANAGED)** 保护机制，防止全局 `pip` 安装破坏系统级依赖。

为了兼顾 **部署稳定性、安装速度** 以及 **底层硬件的完美兼容**，本项目采用了 **APT + PIP 虚拟环境 (System-Site-Packages)** 相结合的"混合优雅"管理范式。

#### ⚙️ 为什么这样设计？

#### 1. 底层硬件与 C 扩展库使用 `apt` 管理
针对涉及底层硬件通信（如 SPI、I2C、GPIO）和包含 C 语言扩展的库（例如 `spidev`, `rpi-lgpio`），我们直接通过系统的 `apt` 包管理器进行安装。

**优势：**
* **🚀 极速部署 (无需现场编译)**：直接安装官方预编译好的二进制 `.deb` 包。彻底告别缓慢的 C 代码现场编译过程，无需在系统中安装 `swig`、`gcc` 或 `liblgpio-dev` 等笨重的构建工具。
* **🛡️ 极致兼容性**：树莓派官方团队已针对特定的硬件架构（aarch64）和最新内核版本对这些包进行了深度优化和测试，杜绝底层通讯 Bug。
* **🧹 保持环境整洁**：生命周期与操作系统升级绑定，统一由系统级包管理器维护。

#### 2. 纯 Python 业务逻辑库使用 `pip` (venv) 管理
对于更新迭代快、或者比较小众的第三方业务库（如 `luma.lcd`, `requests`, `gpiozero` 等），我们使用 Python 虚拟环境 (`venv`) 结合 `pip` 来安装。

**优势：**
* **📦 获取最新特性**：突破 `apt` 仓库版本滞后的限制，自由锁定所需版本。
* **✅ 遵循 PEP 668 规范**：将业务逻辑依赖隔离在虚拟环境中，绝不污染系统全局 Python 环境。

#### 🛠️ Ansible 部署实现

在我们的 Ansible 剧本中，通过开启虚拟环境的**包继承功能**（`--system-site-packages`）完美融合了这两者的优势。

**实现逻辑：**
1. **系统级任务**：通过 `ansible.builtin.apt` 安装底层包（如 `python3-rpi-lgpio`, `python3-spidev`, `python3-smbus`）。
2. **应用级任务**：通过 `ansible.builtin.pip` 创建虚拟环境并安装纯 Python 包，同时设置 `virtualenv_site_packages: yes`。

这使得虚拟环境在隔离业务依赖的同时，能够直接"透传"调用系统 `apt` 安装好的底层硬件通讯模块，实现了极致的部署效率与运行稳定性。

---

### 📦 手动安装依赖与运行指南 (Manual Setup & Dependencies)

如果你不使用 Ansible，需要在树莓派上直接运行 `3.5inch_Capacitive_Touch_LCD.py` Demo，请遵循以下环境配置步骤（特别针对基于 Debian 13 Trixie 的最新 Raspberry Pi OS）：

#### 1. 开启 SPI 和 I2C 接口
树莓派默认关闭这些硬件接口，会导致运行报错 `No such file or directory`。运行前必须开启：
```bash
sudo raspi-config
# 选择 3 Interface Options -> I4 SPI -> Yes
# 选择 3 Interface Options -> I5 I2C -> Yes
sudo reboot
```

#### 2. 安装 Python 系统级依赖
由于最新树莓派系统引入了 PEP 668 保护机制，禁止 `pip` 全局安装。同时，新系统内核弃用了旧的 sysfs GPIO 接口。因此我们必须使用 `apt` 安装，并**使用 `rpi-lgpio` 替代旧的 `RPi.GPIO`**：
```bash
# 1. 修复可能损坏的包状态（例如因为 32位 库导致的未满足依赖）
sudo apt --fix-broken install -y

# 2. 安装所有必需的 Python 第三方依赖
sudo apt install -y python3-rpi-lgpio python3-gpiozero python3-spidev python3-smbus2 python3-pil python3-numpy
```

#### 3. 运行 Demo
赋予执行权限并使用系统自带的 `python3` 运行：
```bash
chmod +x 3.5inch_Capacitive_Touch_LCD.py
./3.5inch_Capacitive_Touch_LCD.py
```

#### 🛠️ 为适配 RPi 4B/Trixie 所做的核心修改

为了让微雪官方的 Demo 能够在最新的树莓派环境下稳定运行，我们在本项目中对原架构进行了以下关键性修改：
1. **触控中断 (TP_INT) 改造为纯轮询模式**: 官方设计中，触控芯片 FT6336U 会通过 `TP_INT` 引脚发送硬件中断。为了避免与其它音频/硬件中断冲突并节省 GPIO 资源，我们**彻底悬空了 `TP_INT` 引脚**。在 Python 代码中，改用**纯轮询模式 (Polling)**（不断调用 `touch.get_touch_xy()` 结合较短的 `time.sleep(0.02)`）来获取触控坐标。
2. **解决底层 GPIO 库冲突**: 将依赖中的 `RPi.GPIO` 替换为新系统官方推荐的兼容包 **`rpi-lgpio`**。这完美解决了由于内核升级导致的 `Conflicts: python3-rpi.gpio` 报错问题。得益于其 API 完全兼容，代码中依旧保留 `import RPi.GPIO` 即可无缝运行。
3. **Python 环境的 Shebang 规范化**: 将主程序首行的 `#!/usr/bin/python` 修改为了跨平台兼容性更好的 `#!/usr/bin/env python3`，确保系统能自动用正确的 Python3 解释器启动脚本。

---

---

## 🧑‍💻 开发调试与架构决策 (Development & Architecture)

### 🛠 开发与调试

如果需要调整屏幕 UI 布局、字体大小或触控的"隐形热区"碰撞边界，只需修改 `scripts/` 目录下的 Python 核心文件，无需重新跑整个 Playbook。

你可以通过以下命令在树莓派上实时查看 UI 与触控服务的日志：
```bash
sudo journalctl -u touch_gui.service -f
```

#### 📸 极客截屏指南

由于 UI 直接由 Python 推送到 SPI 硬件，绕过了 X11/Wayland，无法使用常规截屏工具。我们内置了基于 Linux 信号机制的**内存级截屏**功能。

```bash
# 触发截屏
systemctl --user kill -s SIGUSR1 touchscreen

# 拉取到本地
scp player@<你的树莓派IP>:/tmp/screenshot_*.png ./
```

---

### 🏗️ 架构演进与性能极致优化

#### 1. 突破物理极限的"脏区渲染" (Dirty Rectangle)

SPI 总线在 24MHz 频率下全屏刷新的物理极限仅约 7 FPS。通过引入 `ImageChops.difference` 对比新旧两帧，计算最小变化区域后局部推送，数据传输量降低 90% 以上，实现 30+ FPS 流畅滚动。

#### 2. 告别上帝对象：模块化大拆分

将原本近 500 行的 `main.py` 拆分为三大核心管家：

* 🛡️ **`state_manager.py`**：后台轮询所有数据源，对外提供干净的状态快照。
* 🎛️ **`input_controller.py`**：接管所有坐标碰撞计算，将原始触摸事件翻译为语义化动作。
* 🎨 **`ui_manager.py`**：渲染引擎与屏幕调度，管理所有子界面的流转和脏区渲染。

#### 3. 彻底分离配置边界

* **`ts.ini`**：系统行为参数（硬件 SPI 频率、亮度、屏保超时、滚动节奏）。
* **`ui_config.toml`**：UI 视觉参数（颜色、坐标、字号、图标）。

Python 渲染器成为纯粹的"数据刷子"，切换主题只需替换 `.toml` 文件。

#### 4. 交互升华：零延迟进度条拖拽

拖拽过程中以 30FPS 实时更新滑块视觉位置，手指抬起时才向播放器后端发送跳转指令，完美隔离网络延迟与拖拽手感。

---

#### ⚡ 树莓派 SPI 屏幕驱动图像处理与传输优化总结

在通过 Python 驱动树莓派 SPI 屏幕（如 ST7796，分辨率 480x320）的过程中，原生实现的帧率通常极低（< 5 FPS），且 CPU 占用率极高。通过以下几个核心层面的优化，我们将单帧处理与传输延迟降低到了毫秒级，实现了 30+ FPS 的流畅显示。

#### 1. 核心优化：彻底消除 Python 列表转换开销

**痛点**：原生的 `spidev.writebytes()` 方法强制要求传入一个 **Python List**。一帧 480x320 的 RGB565 图像包含 307,200 个字节。如果使用 `list(data)`，Python 必须在内存中动态创建 30 多万个 `PyLong` 整型对象。这个拆包和打包的过程极其缓慢，耗时远超 SPI 物理传输本身。

**解决方案：使用 `tobytes()` 与 `writebytes2()`**

```python
# 优化前 (极慢)：
# pix = pix.flatten().tolist()
# self.SPI.writebytes(pix)

# 优化后 (极快)：
data = pix.tobytes()
for i in range(0, len(data), 4096):
    self.SPI.writebytes2(data[i:i+4096])
```
*注：分块 4096 字节是为了适配 Linux 默认的 `spidev.bufsiz` 缓冲区大小限制。*

#### 2. 算法优化：Numpy 向量化位运算 (RGB888 转 RGB565)

```python
img = np.asarray(Image)
pix = np.zeros((height, width, 2), dtype=np.uint8)
pix[..., [0]] = np.add(np.bitwise_and(img[..., [0]], 0xF8), np.right_shift(img[..., [1]], 5))
pix[..., [1]] = np.add(np.bitwise_and(np.left_shift(img[..., [1]], 3), 0xE0), np.right_shift(img[..., [2]], 3))
```

#### 3. 内存优化：对象复用与降低 GC 压力

```python
img = Image.new("RGB", (w, h), "BLACK")
draw = ImageDraw.Draw(img)

while True:
    draw.rectangle((0, 0, w, h), fill="black")
    draw.text((0, 0), "Hello Touchscreen!", fill="white")
    dev.show_image(img)
```

#### 4. 架构优化：剥离高频轮询线程

将触摸 I2C 事件的抓取剥离到独立后台守护线程（50Hz），通过线程锁共享数据给主绘图循环，确保触摸事件不因渲染延迟而丢失。

---

#### 🎞️ 图像撕裂问题与滚动优化 (Screen Tearing & Scrolling Optimization)

#### 遇到的问题 (Problem)
在实现界面滚动动画时，我们遇到了明显的**画面撕裂 (Screen Tearing)** 现象。产生这一问题的根本原因在于，树莓派通过 SPI 总线向屏幕推送图像数据的刷新周期，与屏幕本身的硬件级刷新时钟不同步（此类 SPI 屏幕通常没有 VSYNC 垂直同步信号或未连接 TE 引脚）。当画面进行大面积平移滚动时，SPI 数据正在连续覆盖显存的过程中，屏幕同步进行了硬件扫线刷新，导致新旧两帧画面的交替在视觉上产生了明显的横向断层。

#### 解决方法与最终方案 (Solution)
由于硬件层面上无法从 SPI 总线获取 VSYNC 信号，且大面积滚动时“脏区更新”覆盖了整个屏幕而无法减少传输耗时，我们最终采取了从**视觉感知（Visual Perception）**层面来掩盖物理缺陷的策略：

* **极致压缩单帧时间**：将动画的单次滚动循环时间（帧停留间隔）直接减少到了 **20ms**（等效于 50 FPS 的刷新率）。
* **利用视觉暂留 (Persistence of Vision)**：在 20ms 的极高帧率下，每一次滚动的像素位移步长变得极小，且画面切换的速度极快。虽然受限于 SPI 的物理传输机制，微观层面的撕裂在仪器下依然发生，但在人眼视觉暂留效应的平滑下，这种高频微小的撕裂被彻底掩盖。**最终在视觉上已经完全看不出任何撕裂感**，成功实现了极度丝滑流畅的滚动交互体验。

#### 🏛️ UI 架构决策记录 (Architecture Decision Record)

#### 背景

项目在功能迭代过程中，`ui_manager.py` 逐渐积累了多个布尔状态变量（`show_info_screen`、`show_mask_screen`、`show_photo_screen`、`show_volume_popup`）来控制浮层互斥逻辑，同时存在 `dragging_progress` + `drag_progress_ratio` 两个相互冗余的进度条拖拽状态。

#### 决策：精准重构，拒绝过度设计

经过评估，我们**明确拒绝了引入 UI 状态栈（State Stack Pattern）**的重构方案，理由如下：

* 本项目最多 2 层 UI 层级（底层 + 单个浮层），状态栈的收益在 3 层以上才明显。
* 多音源的 UI 差异主要体现在**功能可用性**而非**界面结构**，不需要子类化屏幕状态。
* 单人维护项目，`push/pop` 范式会增加调试成本，违背"简洁可维护"原则。
* 现有性能已经足够（脏区渲染 + 30Hz 主循环），不需要事件驱动重构。

#### 实际执行的三项精准改动

#### 1. 浮层状态改为枚举互斥变量

```python
from enum import Enum, auto

class Overlay(Enum):
    NONE = auto()
    MASK = auto()
    VOLUME = auto()
    INFO = auto()
    PHOTO = auto()

self.active_overlay = Overlay.NONE  # 替代原来的 4 个布尔变量
```

从语言层面强制互斥，消除多状态同时为 `True` 的可能性。`dismiss_screens_on_play` 简化为一句赋值。

#### 2. 进度条拖拽状态合并

```python
# 改前
self.dragging_progress = False
self.drag_progress_ratio = 0.0

# 改后：None 表示未拖拽，float 表示拖拽中的比例值
self.drag_progress_ratio: float | None = None
```

#### 3. 删除 render_key 机制

原有的 `render_key` 在播放状态下因 `is_playing` 条件被短路，实际是死代码。屏保的定时刷新改用直接的秒级时间比较：

```python
current_second = int(current_time)
should_render = (current_second != self._last_saver_second)
```

#### 4. 音量条交互简化

音量弹窗由拖拽式改为**点击式**：点击滑条任意位置即设置对应音量并关闭弹窗，删除所有拖拽中间状态。逻辑更简洁，行为更可预期。

整体改动不超过 60 行，消除了 80% 的互斥维护痛点，主循环结构保持不变。

---

---

## 🤝 贡献与许可

* **许可证**： MIT License - 欢迎自由改造、分发。
* Made with ❤️ for the Maker Community.

---

