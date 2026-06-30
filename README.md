[🇺🇸 English](README.md) | [🇨🇳 中文](README_zh-CN.md)

# 🎵 Ansible_RPI_TouchPlayer

This project aims to transform a Raspberry Pi 4B into a **professional-grade, pure media player** with seamless multi-audio-source switching.
Through a complete hardware and logic rebuild, we upgraded from a traditional monochrome OLED to a **3.5-inch full-color SPI capacitive touchscreen**. Powered by pure Python and `smbus2` polling architecture, it achieves full-screen invisible hotzones for blind-operation-level touch interactions.

The entire system is deployed via **fully automated, idempotent Ansible playbooks**, allowing you to say goodbye to tedious Linux command-line configurations forever.

---

## 📑 Table of Contents

- [Interface Gallery](#interface-gallery)
  - [Audio Sources](#audio-sources)
  - [Interactive Overlays](#interactive-overlays)
  - [Standby & Info](#standby--info)
- [Core Features](#core-features)
  - [Seamless Multi-Source Routing (PipeWire)](#seamless-multi-source-routing-pipewire)
  - [High-Performance Touch UI](#high-performance-touch-ui)
  - [Hardware-Grade Audio Base](#hardware-grade-audio-base)
- [Hardware Guide](#hardware-guide)
  - [Pinout Guide](#pinout-guide)
  - [Backlight Flickering Fix & Hardware PWM](#backlight-flickering-fix--hardware-pwm)
- [Installation & Deployment](#installation--deployment)
  - [Automated Deployment (Ansible)](#automated-deployment-ansible)
  - [Disabling Automatic Updates](#disabling-automatic-updates)
  - [Python Dependency Strategy: Hybrid Elegance](#python-dependency-strategy-hybrid-elegance)
  - [Manual Setup & Dependencies](#manual-setup--dependencies)
- [Development & Architecture](#development--architecture)
  - [Development & Debugging](#development--debugging)
  - [Architecture & Performance Optimization](#architecture--performance-optimization)
- [🎙️ Voice Assistant](#️-voice-assistant)
  - [Technical Breakthrough: Hooking LVA Source Code](#technical-breakthrough-hooking-lva-source-code)
  - [System Selection & Hard-Won Lessons](#system-selection--hard-won-lessons)
  - [Architecture Overview](#architecture-overview)
  - [Voice Assistant UI](#voice-assistant-ui)

---

## 🖼️ Interface Gallery

### 🎼 Audio Sources
<p align="center">
  <img src="UI/Src-Airplay.png" width="32%" alt="AirPlay" />
  <img src="UI/Src-Bluetooth-1.png" width="32%" alt="Bluetooth" />
  <img src="UI/Src_Squeeze-LMS.png" width="32%" alt="Squeezelite" />
</p>

### 🎛️ Interactive Overlays
<p align="center">
  <img src="UI/Main-Volume.png" width="32%" alt="Volume Overlay" />
  <img src="UI/Main-mask.png" width="32%" alt="Action Mask" />
  <img src="UI/Src-Bluetooth-2.png" width="32%" alt="Bluetooth Menu" />
</p>

### 📻 Standby & Info
<p align="center">
  <img src="UI/Screensaver.png" width="32%" alt="Nixie Tube Screensaver" />
  <img src="UI/Photo-Screen.png" width="32%" alt="Photo Frame" />
  <img src="UI/Info.png" width="32%" alt="System Info" />
</p>

### 🎙️ Voice Assistant
<p align="center">
  <img src="UI/Voice-Assistant.png" width="40%" alt="Voice Assistant UI" />
</p>

> Real-time conversation overlay: user speech appears on the right (blue bubbles), assistant replies on the left (gray bubbles). The status bar shows the current pipeline state (listening → processing → responding).

---

## ✨ Core Features

### 🎼 Seamless Multi-Source Routing (PipeWire)
* **🎹 Squeezelite** - Connects to Logitech Media Server to play lossless local music libraries.
* **📱 AirPlay 2** - Streams system-level audio from iPhone/iPad/Mac.
* **🔵 Bluetooth A2DP** - Receives audio streams from any Bluetooth device.

### 🖥️ High-Performance Touch UI
* **Full-Screen Touch Interface**: Designed with clear touch zones and state feedback for the 480x320 screen, improving intuitiveness and latency.
* **Hardware I2C + SPI Isolation**: Touch controls and screen refreshes are transmitted via separate hardware I2C-3 and SPI buses, physically isolating them from the WM8960 audio bus without consuming extra CPU resources.

### 🔊 Hardware-Grade Audio Base
* Uses the **Waveshare WM8960 Sound Board** for high-fidelity I2S hardware decoding output.
  > **💡 Exclusive Driver Optimization**: Since the official Linux driver was designed specifically for the dual-mic HAT version (12.288MHz crystal), using it directly on the single-mic Audio Board version (24MHz crystal) causes severe clock mismatches and pure white noise during recording. We reverse-engineered and generated a custom native Linux driver `wm8960-audio-card.dtbo` specifically for this 24MHz hardware. Ansible will **automatically deploy** this driver and configure the correct ALSA audio routing. For detailed troubleshooting records and technical details, please see [RECORD.md](documents/WM8960/RECORD.md).
* Independent volume control and automatic priority management.

### 🎙️ Offline Local Voice Assistant
* **100% Privacy**: Fully offline, no cloud AI services, no data leaves the device.
* **Chinese NLU**: Natural Chinese commands control smart home devices via Home Assistant.
* **Zero-Idle Overhead**: OpenWakeWord detection adds less than 2% CPU at standby.
* **Technical Breakthrough**: Voice Assistant UI is driven by **patching LVA's `satellite.py` source code** to inject UDP event hooks — enabling real-time conversation display on the touchscreen without modifying the upstream LVA protocol layer.

---

## 🧩 Hardware Guide

### 🧩 Pinout Guide

> **⚠️ Architecture Warning (Conflict Avoidance)**
> This project mounts both an SPI touchscreen and an I2S audio board. You **MUST NOT** connect them using the official default methods from their wikis! Please strictly follow the two wiring tables below, as we have resolved bus conflicts at both the physical and software levels.

#### 1. WM8960 Audio Board (Exclusive Hardware I2C-1 & I2S)
As the core audio unit, the audio board retains exclusive access to the Raspberry Pi's standard audio and control buses.
*(Note: Pin 38 recording data line is kept to satisfy the full-duplex initialization self-check of the Linux ALSA driver, preventing low-level errors)*

| RPi Controller (RPi 4B) | Flow | WM8960 Audio Board | Description |
| :--- | :---: | :--- | :--- |
| **PIN 2 or 4** (5V) | `➔ Power ➔` | **5V** | 5V Main Power |
| **PIN 6 or 9** (GND) | `➔ Ground ➔` | **GND** | Common Ground |
| **PIN 3** (BCM 2) | `↔ Bi-dir ↔` | **SDA** | I2C-1 Audio Control Data |
| **PIN 5** (BCM 3) | `➔ TX ➔` | **SCL** | I2C-1 Audio Control Clock |
| **PIN 12** (BCM 18) | `➔ TX ➔` | **CLK** | I2S Bit Clock (Extremely sensitive, DO NOT preempt) |
| **PIN 35** (BCM 19) | `➔ TX ➔` | **LRCLK (WS)** | I2S L/R Frame Clock |
| **PIN 40** (BCM 21) | `➔ TX ➔` | **DAC (RXSDA)** | **Playback:** Pushes digital audio to the sound card |
| **PIN 38** (BCM 20) | `⬅ RX ⬅` | **ADC (TXSDA)** | **Recording:** Sends mic data to RPi (for driver self-check) |

#### 2. SPI Color Capacitive Touchscreen (SPI0 + Hardware I2C-3 + PWM1)
Product Info: [https://www.waveshare.net/wiki/3.5inch_Capacitive_Touch_LCD]

Display uses standard SPI streaming. Touch uses the RPi 4B's independent hardware I2C-3 bus (physically isolated from the audio bus) and operates in **pure polling mode**, abandoning the interrupt pin.

| LCD Pin No. | LCD Pin | RPi Physical Pin | RPi (BCM) | Description |
| :---: | :--- | :--- | :--- | :--- |
| 1 | VCC | PIN 2 | 5V | Main power for screen and touch chip (5V) |
| 2 | 3V3 | NC | NC | Unconnected (Using 5V power) |
| 3 | GND | PIN 6 | GND | Common Ground |
| 4 | MISO | PIN 21 | BCM 9 | SPI0 Screen data return (Optional) |
| 5 | MOSI | PIN 19 | BCM 10 | SPI0 Pixel data transmission to screen |
| 6 | SCLK | PIN 23 | BCM 11 | SPI0 Transmission Clock |
| 7 | SD_CS | NC | NC | SD Card Chip Select (Unused) |
| 8 | LCD_CS | PIN 24 | BCM 8 | SPI0 Hardware Chip Select |
| 9 | LCD_DC | PIN 22 | BCM 25 | Screen Data/Command Toggle |
| 10 | LCD_RST | PIN 13 | BCM 27 | Screen Display Chip Reset |
| 11 | LCD_BL | PIN 33 | BCM 13 | Screen Backlight Control (PWM1, avoids I2S CLK) |
| 12 | TP_SDA | PIN 7 | BCM 4 | Hardware I2C-3 Touch Data Line |
| 13 | TP_SCL | PIN 29 | BCM 5 | Hardware I2C-3 Touch Clock Line |
| 14 | TP_INT | NC | NC | ❌ **Touch Interrupt:** Pure polling mode used, leave unconnected |
| 15 | TP_RST | PIN 11 | BCM 17 | ✅ **Touch Chip Reset** (Required initialization signal) |

---

### 🌟 Backlight Flickering Fix & Hardware PWM

#### 1. Why does the backlight flicker?
Software PWM relies on CPU thread scheduling to simulate square waves. When system load spikes, millisecond-level scheduling delays occur, swallowing entire high-level pulses at low duty cycles (< 5%), causing noticeable flickering.

**Ultimate Solution**: Enable the Raspberry Pi's native **Hardware PWM** to take over the backlight pin.

#### 2. How to enable Hardware PWM (e.g., BCM 13)
Edit `/boot/firmware/config.txt`:
```ini
# Enable PWM for Backlight Control on BCM 13
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
```
> **⚠️ BCM 12 & BCM 13 Dual-Channel Binding**: `pwm-2chan` forces a reset of both BCM 12 and BCM 13 modes. If BCM 12 is occupied by other peripherals (like I2S), this will break them.

#### 3. Verify Hardware PWM State
```bash
ls -l /sys/class/pwm/        # Expect to see pwmchip0
pinctrl get 13               # Expect to see a0 and PWM
```

#### 4. Software Driver
Control via Linux's native `sysfs` interface to avoid GPIO library meddling:
```bash
echo 1 > /sys/class/pwm/pwmchip0/export
sudo chmod 666 /sys/class/pwm/pwmchip0/pwm1/period \
               /sys/class/pwm/pwmchip0/pwm1/duty_cycle \
               /sys/class/pwm/pwmchip0/pwm1/enable
echo 0       > /sys/class/pwm/pwmchip0/pwm1/duty_cycle   # Clear first
echo 1000000 > /sys/class/pwm/pwmchip0/pwm1/period       # 1000Hz
echo 1       > /sys/class/pwm/pwmchip0/pwm1/enable
```

---

## 🚀 Installation & Deployment

### 🚀 Automated Deployment (Ansible)
All low-level dependencies, service registrations, and complex `dtoverlay` configs (hardware I2C, SPI speedups, etc.) are managed via Ansible with a single click.

#### 🎭 Ansible Role Responsibilities
Based on decoupling and clear responsibilities, the Ansible Roles are strictly divided:
* **`system`**: **(Core Foundation)** Manages system-level global settings and hardware isolation. Handles package updates, env configs, and **centrally manages all hardware interfaces**.
* **`touchscreen`**: Handles application-level deployment of the Python-based SPI screen driver and UI. Focuses purely on source code transmission and Systemd service registration.
* **`bluetooth` / `airplay` / `squeezelite`**: Independently install, configure, and manage their respective audio receiver services.
* **`pipewire` / `volume`**: Sets up the core audio routing engine and handles multi-channel audio mixing logic.

#### 1. Prerequisites
* Target RPi has **Raspberry Pi OS Trixie (64-bit) Lite** (Headless) installed.
* Your local control machine (Mac/Linux) has `ansible` installed.
* **RPi is network-connected with passwordless SSH configured**.

#### 2. Quick Start
Execute on your **local machine**:
```bash
# 1. Clone the project
git clone https://github.com/your-username/Ansible_RPI_TouchPlayer.git
cd Ansible_RPI_TouchPlayer/ansible

# 2. Copy and edit hosts file
cp hosts.ini.example hosts.ini
nano hosts.ini

# 3. Execute automated deployment
ansible-playbook -i hosts.ini site.yml
```

---

### 🛡️ Disabling Automatic Updates
During deployment, the playbook automatically uninstalls `unattended-upgrades` to disable OS automatic updates for stability, uninterrupted playback, and SD card longevity.

---

### 📦 Python Dependency Strategy: Hybrid Elegance
This project runs on modern RPi environments (e.g., Debian 13 Trixie, Linux Kernel 6.12+), which enforce the **PEP 668 (EXTERNALLY-MANAGED)** protection mechanism.
To balance deployment stability, speed, and hardware compatibility, we adopted a **APT + PIP Virtual Environment (System-Site-Packages)** hybrid paradigm.
1. **Low-level Hardware & C-extensions via `apt`**: `spidev`, `rpi-lgpio`, etc.
2. **Pure Python Business Logic via `pip` (venv)**: `luma.lcd`, `requests`, etc.

---

### 📦 Manual Setup & Dependencies
If you aren't using Ansible, follow these steps for **Debian 13 Trixie**:

#### 1. Enable SPI and I2C Interfaces
```bash
sudo raspi-config
# Enable I4 SPI and I5 I2C under Interface Options
sudo reboot
```

#### 2. Install System-Level Python Dependencies
```bash
sudo apt --fix-broken install -y
sudo apt install -y python3-rpi-lgpio python3-gpiozero python3-spidev python3-smbus2 python3-pil python3-numpy
```

#### 3. Run Demo
```bash
chmod +x 3.5inch_Capacitive_Touch_LCD.py
./3.5inch_Capacitive_Touch_LCD.py
```

#### 🛠️ Core Modifications for RPi 4B/Trixie
1. **Touch Interrupt (TP_INT) Converted to Pure Polling**.
2. **Resolved GPIO Library Conflicts** by using `rpi-lgpio`.
3. **Normalized Python Shebangs** to `#!/usr/bin/env python3`.

---

## 🧑‍💻 Development & Architecture

### 🛠 Development & Debugging
To tweak UI layouts or hitboxes, modify the Python files in `scripts/`. No need to re-run the Playbook.
Check real-time logs via:
```bash
sudo journalctl -u touch_gui.service -f
```

#### 📸 Geek Screenshot Guide
Since the UI is pushed directly via Python to SPI hardware, bypassing X11/Wayland, we built an in-memory screenshot function triggered via Linux signals:
```bash
systemctl --user kill -s SIGUSR1 touchscreen
scp player@<rpi-ip>:/tmp/screenshot_*.png ./
```

---

### 🏗️ Architecture & Performance Optimization

#### 1. Breaking Physical Limits with "Dirty Rectangle"
SPI bus physical limits at 24MHz allow only ~7 FPS for full-screen refreshes. Using `ImageChops.difference`, we calculate minimal changing areas, reducing data transfer by 90%+ and achieving smooth 30+ FPS.

#### 2. Module Decoupling
Broke down the massive 500-line `main.py` into:
* `state_manager.py`: Background polling and state snapshots.
* `input_controller.py`: Touch coordinate translation.
* `ui_manager.py`: Render engine and dirty rectangle management.

#### 3. Configuration Boundary Separation
* `ts.ini`: System behavior parameters (SPI freq, timeouts).
* `ui_config.toml`: Visual parameters (colors, coordinates).

#### 4. Zero-Latency Progress Bar Dragging
Real-time 30FPS visual updates during drags, dispatching backend commands only upon release to isolate network latency.

---

#### ⚡ SPI Screen Image Processing Optimization
Optimized raw `spidev.writebytes()` by eliminating Python List conversion overhead.
Using `tobytes()` and `writebytes2()` with chunking handles RGB565 data incredibly fast. Also vectorized RGB888 to RGB565 conversion using Numpy bitwise operations.

#### 🎞️ Screen Tearing & Scrolling Optimization
When implementing scrolling animations, we encountered severe **Screen Tearing**. This occurs because the SPI bus pushes data asynchronously to the screen's hardware refresh clock (lacking VSYNC).
**Solution**: We compressed the per-frame interval to **20ms** (50 FPS). By leveraging the persistence of vision at such high frame rates, the microscopic physical tearing is entirely smoothed out visually, achieving a buttery-smooth scrolling experience.

#### 🏛️ UI Architecture Decision Record
* **Rejected UI State Stack Pattern**: Our project has a max of 2 layers. A stack increases debugging costs.
* **Adopted Enum Overlays**: Replaced multiple booleans with an `Overlay` Enum to enforce mutual exclusivity.

#### 🚀 Extreme Performance Optimization: Maxing Out 4GB RAM

For a media player and voice assistant project focused on zero-latency response, the poor I/O throughput of the Raspberry Pi's SD card is often a fatal bottleneck. When audio slices are frequently generated by `wyoming` services, this I/O blocking can cause dropped frames in UI animations, sluggish touch interactions, or delayed wake-word responses.

Since the Raspberry Pi 4B has 4GB of RAM (which is more than enough for this project), we implemented the following **hardcore low-level I/O isolation and memory tuning** via Ansible's `system` role to achieve "absolute zero latency":

1. **Completely Disable Swap**: Thoroughly uninstalled `dphys-swapfile`. This forces the system to run 100% in pure physical memory, permanently avoiding the massive latency spikes caused by SD card paging.
2. **Mount Temp Directories as RAM Disks**: Mounted `/tmp` and `/var/tmp` as `tmpfs`. All temporary files (such as Wyoming's voice chunks and caches) are created and destroyed instantly in pure physical memory.
3. **Persistent Journal Storage**: Enabled `systemd-journald` disk persistence so that service logs survive unexpected power losses or crashes, making debugging possible.
4. **Robust Kernel Sysctl Tuning**:
   - `vm.vfs_cache_pressure = 50`: Instructs the kernel to aggressively hold onto directory and file inode caches, enabling "zero seek time" for Python module imports and UI icon loading.
   - `vm.dirty_ratio = 20` & `vm.dirty_background_ratio = 10`: Safely buffers as many disk write operations as possible in RAM (while balancing the risk of sudden power loss), allowing the kernel to flush them to the SD card silently in the background.

After these optimizations, AI engines reside fully in memory, high-frequency I/O occurs entirely in RAM, and the remaining memory is pushed to its limits by the Linux Page Cache—bringing the player's fluidity close to the physical limit!

---

## 🎙️ Voice Assistant

This project integrates a fully **offline, local** intelligent voice assistant, enabling natural Chinese voice control of Home Assistant smart home devices — all running on the Raspberry Pi 4B itself, with zero cloud dependency.

### Technical Breakthrough: Hooking LVA Source Code

The Voice Assistant UI — the real-time conversation overlay shown on the touchscreen — **could not be achieved through LVA's standard configuration alone**.

LVA (Linux Voice Assistant) provides event callback scripts (`LVA_ON_WAKE_WORD`, `LVA_ON_STT_END`, `LVA_ON_TTS_START`, `LVA_ON_TTS_END`) that fire at key pipeline stages. However, these hooks carry **no text payload** for the transcript or TTS response, making it impossible to display conversation content on-screen through official means.

**Our breakthrough: we directly patched LVA's `satellite.py` source code**, injecting UDP sends to port `10701` at the precise internal points where text data is available inside the pipeline. This allows the Python UI layer to receive structured JSON events — including the recognized speech text and the assistant's reply — and render them as chat bubbles in real time.

```
LVA satellite.py (patched)
    ├─ on wake word  →  UDP {"event": "awake"}
    ├─ on STT end    →  UDP {"event": "transcript", "text": "关闭小米台灯"}
    ├─ on TTS start  →  UDP {"event": "tts-start"}
    ├─ on synthesize →  UDP {"event": "synthesize", "text": "小米台灯已关闭"}
    └─ on TTS end    →  UDP {"event": "done"}
                              ↓
                   assistant_listener.py (port 10701)
                              ↓
                   StateManager → UIManager
                              ↓
                   Real-time chat bubble overlay on touchscreen
```

The patched `satellite.py` is version-controlled in `roles/voiceassistant/files/` and deployed automatically by Ansible, ensuring full reproducibility.

---

### System Selection & Hard-Won Lessons

The final architecture was reached only after thoroughly evaluating and rejecting two earlier stacks.

#### Stage 1: wyoming-satellite + Whisper + Piper (Abandoned)

The initial design followed the mainstream Home Assistant satellite pattern.

**Why it failed:**

| Problem | Root Cause | Verdict |
|---------|-----------|---------|
| **"2-second disconnect" loop** | Wyoming protocol ping/pong race condition between HA and satellite — a known protocol-layer bug, unfixable by tuning | Fatal |
| **Whisper hallucination deadlock** | Autoregressive decoder loops on silence/noise, generating prompt text for 2+ minutes on ARM | Unusable on RPi |
| **Piper Chinese TTS silent output** | `ModuleNotFoundError: No module named 'unicode_rbnf'` — Chinese phonemization fails, outputs zero-byte WAV | Broken |
| **Both projects archived** | `wyoming-satellite` archived Jan 27 2026; `wyoming-piper` also unmaintained | No future |

#### Stage 2: LVA + Sherpa-ONNX (Current — Stable)

LVA abandons the Wyoming protocol entirely and uses the **ESPHome native API** — eliminating the ping/pong timeout at the protocol level. STT and TTS run locally on the RPi via **Sherpa-ONNX**, bypassing the J3455 VM's lack of AVX/AVX2 (Whisper on J3455 takes 5–10 s per short phrase).

| Component | Choice | Reason |
|-----------|--------|--------|
| Satellite | LVA (ESPHome API) | Stable connection; actively maintained by OHF |
| Wake word | OpenWakeWord `ok_nabu` | Built into LVA; open source; no API key |
| STT | Sherpa-ONNX SenseVoice-int8 | CTC architecture; no hallucination deadlock; RAM-resident |
| TTS | Sherpa-ONNX Matcha-Icefall + Vocos | Pure C++; natural Chinese voice; no dependency hell |

**Core design principle**: pause music on wake word → CPU goes full-throttle for inference → resume after TTS. This eliminates the need for AEC entirely and keeps idle overhead under 2%.

---

### Architecture Overview

```
Microphone (PipeWire)
    ↓
LVA (OpenWakeWord — detects "ok nabu")
    ├─ patched satellite.py → UDP 10701 → Touchscreen UI (chat bubbles)
    └─ ESPHome API → Home Assistant Assist Pipeline
                          ├─ Wyoming Integration → Sherpa-ONNX STT (port 10300)
                          ├─ NLU intent matching (custom_sentences zh_CN)
                          └─ Wyoming Integration → Sherpa-ONNX TTS (port 10200)
                                                        ↓
                                               LVA → PipeWire → Speaker
```

All components are deployed as user-level Systemd services (`player` user) via Ansible's `voiceassistant` role.

---

### Voice Assistant UI

<p align="center">
  <img src="UI/Voice-Assistant.png" width="45%" alt="Voice Assistant UI" />
</p>

The UI overlay is driven entirely by UDP events from the patched `satellite.py`. When the wake word fires, a full-screen voice session mask appears. User speech renders as right-aligned blue bubbles; assistant replies appear as left-aligned gray bubbles. The status bar reflects the current pipeline state in real time.

`assistant_listener.py` listens on port `10701`, feeds events into `StateManager`, and the main render loop updates the screen within the existing 30 FPS dirty-rectangle pipeline — zero additional latency layer.

---

## 🤝 Contribution & License
* **License**: MIT License - Free to modify and distribute.
* Made with ❤️ for the Maker Community.
