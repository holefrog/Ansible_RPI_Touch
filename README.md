# 🎵 Ansible_RPI_TouchPlayer

[🇨🇳 中文版本](README_zh-CN.md) | [💬 反馈与问题](https://github.com/holefrog/Ansible_RPI_Touch/issues)

---

## 🖼️ UI Preview (Interface Gallery)

### 🎼 Seamless Multi-Source Audio Switching (Audio Sources)
<p align="center">
  <img src="UI/Src-Airplay.png" width="32%" alt="AirPlay" />
  <img src="UI/Src-Bluetooth-1.png" width="32%" alt="Bluetooth" />
  <img src="UI/Src_Squeeze-LMS.png" width="32%" alt="Squeezelite" />
</p>

### 🎛️ Touch Interaction & Overlays (Interactive Overlays)
<p align="center">
  <img src="UI/Main-Volume.png" width="32%" alt="Volume Overlay" />
  <img src="UI/Main-mask.png" width="32%" alt="Action Mask" />
  <img src="UI/Src-Bluetooth-2.png" width="32%" alt="Bluetooth Menu" />
</p>

### 📻 Screensaver & Info Screen (Standby & Info)
<p align="center">
  <img src="UI/Screensaver.png" width="32%" alt="Nixie Tube Screensaver" />
  <img src="UI/Photo-Screen.png" width="32%" alt="Photo Frame" />
  <img src="UI/Info.png" width="32%" alt="System Info" />
</p>

### 🎙️ Intelligent Voice Assistant (Voice Assistant)
<p align="center">
  <img src="UI/Voice-Assistant.png" width="40%" alt="Voice Assistant UI" />
</p>

> Real-time conversation overlay: Blue bubbles on the right show user speech-to-text, gray bubbles on the left show assistant responses, and the status bar at the bottom displays the current stage (Awake → Recording → Responding) in real-time.

---

## 🎯 What You Get (30-Second Summary)

Transform a **Raspberry Pi 4B** into a **premium, high-fidelity media player** with a professional touchscreen UI.

✨ **Key Features:**
- **Touchscreen UI** with blind-operation-level touch zones (480×320, 30+ FPS)
- **Seamless multi-source audio**: AirPlay ↔ Bluetooth ↔ Squeezelite (one-tap switching)
- **Offline voice assistant** in Chinese (100% privacy, zero cloud)
- **Full hardware isolation**: I2C + SPI buses physically separated to prevent conflicts
- **Zero-maintenance deployment**: Fully automated via Ansible (idempotent, reproducible)

**Requirements:**
- Time: 48 hours (8h hardware assembly + 8h Ansible deployment + 32h fine-tuning)
- Cost: ~$250 USD (RPi 4B + audio board + touchscreen)
- Skill: Intermediate (soldering, basic Linux)
- Reward: Professional-grade media player for your living room 🏆

---

## 📑 Quick Navigation

| I want to... | Jump to |
|---|---|
| **Set up immediately** | [Installation & Deployment](#-installation--deployment) |
| **Understand the hardware** | [Hardware Pinout Guide](#-pinout-guide) |
| **Customize the UI** | [Development & Architecture](#-development--architecture) |
| **Set up voice assistant** | [Voice Assistant Setup](#-voice-assistant-setup) |
| **Fix a problem** | [Troubleshooting & FAQ](#-troubleshooting--faq) |
| **Learn the architecture** | [Architecture Decision Records](#-architecture-decisions) |

---

## ✨ Core Features

### 🎼 Seamless Multi-Source Audio Routing (PipeWire)

Three audio sources, one seamless player:

- **🎹 Squeezelite** → Logitech Media Server (lossless local music)
- **📱 AirPlay 2** → iPhone/iPad/Mac (system-level audio streaming)
- **🔵 Bluetooth A2DP** → Any Bluetooth device (simple wireless)

**How it works:** PipeWire automatically manages mixing and switching. Pause Spotify on your phone, music from LMS continues without interruption.

### 🖥️ High-Performance Touch UI

**480×320 SPI Display** powered by:
- **Dirty Rectangle Optimization**: Only redraw changed pixels → 90%+ SPI bandwidth reduction → 30+ FPS animations
- **Pure Polling Mode**: No GPIO library conflicts. Hardware I2C-3 handles touch, isolated from audio I2C-1
- **Zero-Latency Drags**: Real-time visual feedback (30 FPS) during progress bar drags; backend commands fire only on release

**Result:** Buttery-smooth scrolling, snappy touch response, professional UX.

### 🔊 Hardware-Grade Audio (WM8960 Sound Board)

**Why WM8960?**
- H-Bridge amplifier for direct speaker connection (no additional amp needed)
- I2S hardware audio codec (bitperfect playback)
- Dual microphones for future voice control

**Exclusive Driver Optimization:**
The official WM8960 driver was designed for the **dual-mic HAT** (12.288 MHz crystal). Using it on the **single-mic Audio Board** (24 MHz crystal) causes clock mismatch → pure white noise during recording.

**Our solution:** Custom native Linux driver `wm8960-audio-card.dtbo` (reverse-engineered from kernel source). Ansible deploys it automatically with correct ALSA routing. See [WM8960 Technical Record](documents/WM8960/RECORD.md) for details.

### 🎙️ Offline Local Voice Assistant

**Zero Cloud, 100% Privacy**

- **English + Chinese NLU**: Natural speech control
- **Zero-Idle Overhead**: OpenWakeWord detection uses <2% CPU at standby
- **Real-Time UI**: Voice/response text displayed as chat bubbles on touchscreen

**Technical Breakthrough:** We patched LVA's `satellite.py` source to inject UDP hooks at the exact internal points where text data is available. This enables real-time transcript display without modifying the upstream LVA protocol. See [Voice Assistant Deep Dive](#-voice-assistant-deep-dive).

---

## 📦 Before You Start: Pre-Deployment Checklist

### ✅ Hardware Checklist

- [ ] **Raspberry Pi 4B** (2GB+, 4GB recommended)
  - Other RPi models (4, 5, CM4) may work but are untested;
  
- [ ] **Waveshare WM8960 Audio Board**
  - Single-mic version (not the dual-mic HAT)
  - Soldered to RPi GPIO (or use 2.54mm header pins for reversibility)
  
- [ ] **3.5" Capacitive Touch LCD (ST7796)**
  - 480×320 resolution
  - FT6336U touch controller
  - Link: https://www.waveshare.net/wiki/3.5inch_Capacitive_Touch_LCD
  
- [ ] **Power Supply**
  - 5V/3A minimum (5V/5A recommended for stability)
  - USB-C connector for RPi 4B
  
- [ ] **SD Card**
  - Class 10, 16GB+ (faster cards = faster boot)
  - Will be erased during OS installation

- [ ] **Soldering Kit** (if connecting audio board directly)
  - Soldering iron, solder, flux
  - Desoldering wick (for mistakes)

### 💻 Software Checklist

**On your Raspberry Pi:**

- [ ] **OS:** Raspberry Pi OS Trixie (64-bit Lite)
  ```bash
  # After flashing, verify:
  uname -m          # Should output: aarch64
  lsb_release -cs   # Should output: trixie
  ```
  
  > **Note:** Trixie is the latest (2024). 
  
- [ ] **Network:** WiFi or Ethernet connected
  ```bash
  # Verify:
  ping 8.8.8.8
  ```

- [ ] **SSH:** Passwordless key authentication ready
  ```bash
  # On your control machine (Mac/Linux):
  ssh-copy-id -i ~/.ssh/id_rsa pi@<rpi-ip>
  
  # Verify:
  ssh -i ~/.ssh/id_rsa pi@<rpi-ip> "echo OK"
  # Output: OK (no password prompt)
  ```

**On your control machine (Mac/Linux):**

- [ ] **Ansible** 2.9+
  ```bash
  ansible --version
  # Output: ansible [core 2.X.X] ...
  
  # If not installed:
  pip3 install ansible
  ```

- [ ] **Python** 3.8+
  ```bash
  python3 --version
  ```

- [ ] **Git** (to clone this repository)
  ```bash
  git --version
  ```

---

## 🚀 Installation & Deployment

### 🎭 Choose Your Path

#### **Path 1: Full Automation (Recommended) ⭐**

**For:** Users who want a plug-and-play experience

**Time:** ~30 minutes (plus 30 min waiting for services to start)

**Steps:**

```bash
# 1. Clone the project on your control machine
git clone https://github.com/holefrog/Ansible_RPI_Touch.git
cd Ansible_RPI_Touch/ansible

# 2. Configure target RPi
cp inventory/hosts.ini.example inventory/hosts.ini
nano inventory/hosts.ini
# Edit: [rpi_players] section
#   my_player ansible_host=<RPi-IP> ansible_user=pi

# 3. Run automated deployment
ansible-playbook -i inventory/hosts.ini site.yml

# 4. Grab a coffee ☕ (takes 15-30 min)
# When done, touch screen will light up automatically
```

**Success Indicators:**
- Touch screen displays main menu
- System info visible in top-right corner
- Speaker outputs audio when you play something

**Troubleshooting this path:**
- If deployment fails midway, re-run the playbook. Ansible is idempotent (safe to re-run).
- For permission errors, ensure `ansible_user=pi` in hosts.ini has sudoers access.
- Check logs: `ansible-playbook -i inventory/hosts.ini site.yml -v`

---

#### **Path 2: Step-by-Step Manual Setup (Learning-Focused)**

**For:** Developers who want to understand each step

**Prerequisites:** Read [Manual Setup & Dependencies](#-manual-setup--dependencies)

**Steps:**

```bash
# 1. Enable hardware interfaces on RPi
ssh pi@<rpi-ip>
sudo raspi-config
# → Interface Options → I4 SPI → Enable
# → Interface Options → I5 I2C → Enable
# → Reboot

# 2. Install system Python libraries
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-rpi-lgpio python3-spidev python3-smbus2 \
                    python3-pil python3-numpy

# 3. Deploy modules individually (instead of full site.yml)
# You can now manually execute individual role playbooks:
# - roles/system/tasks/main.yml (hardware config)
# - roles/pipewire/tasks/main.yml (audio)
# - roles/touchscreen/tasks/main.yml (UI)
```

See detailed instructions in [Manual Setup](#-manual-setup--dependencies).

---

#### **Path 3: Local Development Mode (UI Customization)**

**For:** Developers modifying the UI without full Ansible re-deployment

**Prerequisites:** Path 1 or Path 2 completed first

**Workflow:**

```bash
# SSH into RPi
ssh player@<rpi-ip>

# Edit UI config without Ansible
cd /opt/touchscreen-ui
nano ui_config.toml           # Visual parameters (colors, font sizes)
nano ui_components.py        # Component definitions
nano main.py                  # Main UI loop

# Restart service to reload
sudo systemctl restart touchscreen.service

# Monitor logs in real-time
sudo journalctl -u touchscreen.service -f
```

**No Ansible re-run needed!** Changes take effect immediately.

---

### ⏱️ Deployment Timeline

| Step | Time | What Happens |
|------|------|--------------|
| Pre-checks | 2 min | Ansible verifies connectivity, permissions |
| System updates & packages | 8 min | apt upgrade, installs Python deps |
| Hardware config (dtoverlay, I2C, SPI) | 3 min | Kernel device trees, pin modes |
| **Audio stack** (PipeWire, WM8960 driver) | 5 min | Audio services start |
| **AirPlay / Bluetooth / Squeezelite** | 4 min | Streaming services enabled |
| **Touchscreen UI** | 4 min | Python app deployed, systemd service registered |
| **Voice Assistant** (LVA, Sherpa-ONNX) | 3 min | Offline speech models downloaded (~500 MB) |
| **Post-config** (memory optimization, cleanup) | 2 min | RAM disks, sysctl tuning |
| **Total** | **~30 min** | ✅ System ready |

---

## 🧩 Hardware Setup

### 🔌 Pinout Guide

⚠️ **Critical Warning:** This project uses **both SPI (touchscreen) and I2S (audio)** on a 4-pin interface. Incorrect wiring causes:
- Audio distortion or silence
- Touchscreen flickering or unresponsiveness
- GPIO conflicts

**Follow the tables below exactly. Do NOT use the default wiring from peripheral wikis.**

---

#### 1️⃣ WM8960 Audio Board (I2C-1 + I2S)

| RPi Pin (Physical) | RPi GPIO | Direction | Audio Board | Purpose |
|---|---|---|---|---|
| PIN 2 or 4 | 5V | → Power → | **5V** | Power input |
| PIN 6 or 9 | GND | → GND → | **GND** | Ground |
| **PIN 3** | **GPIO 2** | **↔ Bi-dir ↔** | **SDA** | I2C-1 data (audio control) |
| **PIN 5** | **GPIO 3** | **↔ Bi-dir ↔** | **SCL** | I2C-1 clock (audio control) |
| PIN 12 | GPIO 18 | → TX → | **CLK** | I2S bit clock (**⚠️ DO NOT TOUCH**) |
| PIN 35 | GPIO 19 | → TX → | **LRCLK** | I2S L/R frame clock |
| PIN 40 | GPIO 21 | → TX → | **DAC (RXSDA)** | Playback audio data |
| PIN 38 | GPIO 20 | ← RX ← | **ADC (TXSDA)** | Recording (mic) - Keep for driver self-check |

**Key Notes:**
- GPIO 18 is **I2S bit clock** — extremely sensitive, pre-emption causes artifacts
- Keep GPIO 20 (ADC) connected even if you don't record; Linux driver requires it for initialization
- Power must be **stable 5V** (noisy power → audio jitter)

---

#### 2️⃣ 3.5" Capacitive Touchscreen (SPI0 + I2C-3 + PWM)

| Screen Pin | Signal | RPi Physical Pin | RPi GPIO | Purpose | Notes |
|---|---|---|---|---|---|
| 1 | VCC | PIN 2 | 5V | Power | Use 5V, not 3.3V |
| 2 | 3V3 | **NC** | — | Unused | — |
| 3 | GND | PIN 6 | GND | Ground | — |
| 4 | MISO | PIN 21 | GPIO 9 | SPI data-in | Optional (display is unidirectional) |
| 5 | MOSI | PIN 19 | GPIO 10 | SPI data-out | Pixel data to screen |
| 6 | SCLK | PIN 23 | GPIO 11 | SPI clock | Pixel clock |
| 7 | SD_CS | **NC** | — | SD card CS | Unused (no SD card on this board) |
| **8** | **LCD_CS** | **PIN 24** | **GPIO 8** | **SPI chip select** | **Must use GPIO 8** |
| **9** | **LCD_DC** | **PIN 22** | **GPIO 25** | **Data/Cmd toggle** | Controls SPI packet type |
| **10** | **LCD_RST** | **PIN 13** | **GPIO 27** | **Screen reset** | Pulse on startup |
| **11** | **LCD_BL** | **PIN 33** | **GPIO 13** | **Backlight PWM** | **Hardware PWM1** (avoids I2S interference) |
| **12** | **TP_SDA** | **PIN 7** | **GPIO 4** | **I2C-3 data** | Touch (isolated from audio I2C-1) |
| **13** | **TP_SCL** | **PIN 29** | **GPIO 5** | **I2C-3 clock** | Touch (isolated from audio I2C-1) |
| 14 | TP_INT | **NC** | — | ❌ **Not used** | Pure polling mode (no interrupts) |
| **15** | **TP_RST** | **PIN 11** | **GPIO 17** | **Touch reset** | Initialization signal |

**Key Notes:**
- SPI0 is the only SPI bus on RPi 4B; no alternatives
- I2C-3 is **physically isolated** from I2C-1 (audio control) — no conflicts
- PWM1 (GPIO 13) is explicitly chosen to avoid I2S clock (GPIO 18) conflicts
- Touch uses **pure polling** (no interrupt pin) → solves contention issues

---

### 💡 Backlight Flickering & Hardware PWM Setup

#### Why Does Backlight Flicker?

Software PWM (bit-banging GPIO) relies on CPU threads to generate square waves. Under system load, scheduling delays drop milliseconds → entire PWM pulses are lost → visible flicker at low brightness.

**Solution:** Enable Raspberry Pi's native **Hardware PWM** (dedicated hardware counter).

#### How to Enable Hardware PWM

Edit `/boot/firmware/config.txt`:

```ini
# Enable Hardware PWM for Backlight on GPIO 13 (PWM1)
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
```

**⚠️ Critical:** `pwm-2chan` forces both GPIO 12 and GPIO 13 to PWM mode. If GPIO 12 is used by other hardware (like I2S CLK), this breaks them.

**Solution:** Ansible verifies I2S clock on GPIO 18 (not GPIO 12), so no conflict.

#### Verify Hardware PWM is Active

```bash
ls -la /sys/class/pwm/pwmchip0/pwm1/

# Expected output:
# duty_cycle  enable  period  polarity  uevent

# Check GPIO 13 mode:
pinctrl get 13
# Expected: a0, PWM
```

---

## 🧑‍💻 Development & Architecture

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              Ansible Roles (Deployment)              │
├─────────────────────────────────────────────────────┤
│ system        → Hardware isolation (dtoverlay, I2C)  │
│ pipewire      → Audio engine & multi-source mixing   │
│ airplay       → AirPlay receiver (shairport-sync)    │
│ bluetooth     → Bluetooth A2DP (auto-pair)           │
│ squeezelite   → LMS client (Logitech Media Server)   │
│ volume        → Master volume control service        │
│ touchscreen   → Python UI + screen driver            │
│ voiceassistant→ LVA + offline speech recognition    │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│          Python Application Layer                     │
├─────────────────────────────────────────────────────┤
│ main.py             → Entry point, service loop      │
│ ui_manager.py       → Render engine (dirty rect)     │
│ state_manager.py    → Background state polling       │
│ input_controller.py → Touch coordinate mapping       │
│ assistant_listener.py → Voice UDP event handler      │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│      Hardware I/O (Pure SPI + I2C)                    │
├─────────────────────────────────────────────────────┤
│ st7796.py        → ST7796 SPI display driver         │
│ ft6336u.py       → FT6336U I2C touch controller      │
│ hardware_display.py → Display backlight PWM control  │
└─────────────────────────────────────────────────────┘
```

### Development Workflow

#### 1. **Modify Configuration (No Restart)**

Edit `ui_config.toml`:
```toml
[screen]
width = 480
height = 320
spi_speed = 24000000  # 24 MHz

[ui]
main_bg_color = "#000000"
font_size = 24
```

Changes take effect immediately after `main.py` reloads.

#### 2. **Modify UI Layout (Systemd Restart)**

Edit `main.py`, `ui_screen_main.py`, or `ui_components.py`:
```bash
ssh player@<rpi-ip>
cd /opt/touchscreen-ui
nano ui_screen_main.py
sudo systemctl restart touchscreen.service
```

Check logs:
```bash
sudo journalctl -u touchscreen.service -f
```

#### 3. **Modify Audio Routing (PipeWire Restart)**

Edit `/etc/pipewire/pipewire.conf` or `/etc/alsa/asound.conf`:
```bash
sudo systemctl restart pipewire.service
```

#### 4. **Run Local Test Script**

```bash
# On RPi:
python3 /opt/touchscreen-ui/test_screen.py
# Displays gradient, measures SPI timing, tests touch
```

---

### Performance Optimization Techniques

#### 1. **Dirty Rectangle Algorithm**

Problem: Full SPI screen refresh (480×320 RGB565) at 24MHz = ~7 FPS only.

Solution: **Dirty Rectangle** — only redraw changed pixels.

```python
from PIL import ImageChops

frame_prev = Image.new('RGB', (480, 320))
frame_curr = render_ui()

# Find minimal bounding box of changes
diff = ImageChops.difference(frame_prev, frame_curr)
bbox = diff.getbbox()

if bbox:
    # Only send changed rectangle to SPI
    spi_write_rect(frame_curr, bbox)
    
frame_prev = frame_curr
```

**Result:** 90%+ bandwidth reduction → **30+ FPS** smooth animations.

#### 2. **Module Decoupling**

Original: 500-line monolithic `main.py`

Refactored:
- `state_manager.py` — Background state polling (runs in thread)
- `input_controller.py` — Touch coordinate translation (no UI blocking)
- `ui_manager.py` — Render pipeline (manages dirty rects)
- `main.py` — Glue layer, service loop

**Benefit:** Changes to touch handling don't affect rendering; testable units.

#### 3. **RAM Disk for Zero-Latency I/O**

Problem: SD card I/O blocking → dropped UI frames.

Solution: Mount `/tmp` and `/var/tmp` as `tmpfs` (RAM disks).

```bash
# Ansible auto-configures:
mount | grep tmpfs
# /dev/shm on /tmp type tmpfs
# /dev/shm on /var/tmp type tmpfs
```

All temporary files (voice chunks, caches) live in RAM → no SD card I/O jitter.

#### 4. **Kernel Sysctl Tuning**

Ansible applies:
```
vm.vfs_cache_pressure = 50    # Aggressively cache inodes (faster icon loading)
vm.dirty_ratio = 20           # Buffer disk writes in RAM
vm.dirty_background_ratio = 10
swappiness = 0                # Disable swap (pure memory priority)
```

---

### Debugging Tips

#### **Screenshot Capture** (In-Memory)

Since UI runs directly on SPI hardware (no X11/Wayland), use a built-in signal handler:

```bash
# On control machine:
ssh player@<rpi-ip> "systemctl --user kill -s SIGUSR1 touchscreen"

# PNG screenshots are written to /tmp/ on RPi:
scp player@<rpi-ip>:/tmp/screenshot_*.png ./
```

#### **Live Log Streaming**

```bash
ssh player@<rpi-ip> "sudo journalctl -u touchscreen.service -f"
```

#### **SPI Performance Profiling**

```python
import time
from st7796 import ST7796

display = ST7796()
t0 = time.time()
display.write_rect(frame, (0, 0, 480, 320))  # Full screen
print(f"SPI transfer: {(time.time() - t0) * 1000:.1f} ms")
# Expected: ~50-60 ms for full frame @ 24 MHz
```

---

## 🎙️ Voice Assistant Deep Dive

### System Architecture

```
Microphone (via PipeWire)
    ↓
LVA Daemon (Linux Voice Assistant)
    ├─ OpenWakeWord detection ("ok nabu")
    │       ↓
    │   [Patched satellite.py]
    │       → UDP port 10701 {"event": "awake"}
    │
    ├─ Pause playback (free CPU for inference)
    │
    ├─ Wyoming STT Integration → Sherpa-ONNX (port 10300)
    │       ↓
    │   Transcription: "关闭小米台灯" (Turn off Xiaomi lamp)
    │       → UDP {"event": "transcript", "text": "..."}
    │
    ├─ Home Assistant Intent Matching
    │       ↓
    │   Matched: device=lamp, action=off
    │
    ├─ Wyoming TTS Integration → Sherpa-ONNX (port 10200)
    │       ↓
    │   Response: "小米台灯已关闭" (Xiaomi lamp is off)
    │       → UDP {"event": "synthesize", "text": "..."}
    │
    └─ Audio playback via PipeWire
            ↓
        Speaker output

              ↓↓↓
    [assistant_listener.py] (port 10701)
              ↓
    StateManager → UIManager
              ↓
    Real-time chat bubble overlay on touchscreen
```

### Technical Breakthrough: UDP Patching

**Problem:** LVA provides callback scripts but **no text payload**:
```bash
# Standard LVA callbacks:
LVA_ON_WAKE_WORD=""              # ✗ Empty
LVA_ON_STT_END=""                # ✗ No transcript
LVA_ON_TTS_START=""              # ✗ No reply text
```

**Cannot display conversation without text!**

**Our Solution:** Patch LVA's `satellite.py` source code to inject UDP sends at exact points where text is available inside the inference pipeline:

```python
# In satellite.py (patched)
def on_transcript(text):
    # ... inference logic ...
    socket.sendto(json.dumps({
        "event": "transcript",
        "text": text  # ← Text data injected here
    }).encode(), ("127.0.0.1", 10701))
```

**Advantages:**
1. **Zero protocol changes** — LVA API unchanged
2. **Real-time text** — Display happens immediately
3. **Version-controlled** — Patched `satellite.py` in `roles/voiceassistant/files/`

### Why Not Wyoming?

We evaluated `wyoming-satellite` (mainstream HA integration) and rejected it:

| Issue | Root Cause | Severity |
|---|---|---|
| 2-second disconnect loop | Protocol ping/pong race condition | **Fatal** |
| Whisper hallucination | Autoregressive decoder loops on ARM silence | **Fatal** |
| Piper Chinese TTS silent | Missing `unicode_rbnf` phonemization | **Blocking** |
| Projects archived | `wyoming-satellite` abandoned Jan 2026 | **No future** |

**LVA is the stable alternative.**

### Voice Assistant UI

The UI overlay (chat bubbles) is a **separate Python thread** managed by `assistant_listener.py`:

```python
# Runs in StateManager background thread
listener = AssistantListener(port=10701)

while True:
    event = listener.recv()  # Blocking UDP receive
    
    if event["event"] == "transcript":
        state.assistant_messages.append({
            "role": "user",
            "text": event["text"],
            "timestamp": time.time()
        })
    elif event["event"] == "synthesize":
        state.assistant_messages.append({
            "role": "assistant",
            "text": event["text"]
        })
    
    # Render thread picks up state.assistant_messages
    # and draws chat bubbles in real-time
```

**Key insight:** UI updates are **decoupled from inference**. TTS generation doesn't block rendering.

---

## ⚙️ Manual Setup & Dependencies

If you skip Ansible and set up manually:

### 1. Enable Hardware Interfaces

```bash
sudo raspi-config
# Interface Options → I4 SPI → Enable
# Interface Options → I5 I2C → Enable
# Advanced Options → Hardware I2C → Enable I2C-3
# Reboot

# Verify:
ls /dev/spi*   # Should see: /dev/spidev0.0
i2cdetect -l   # Should see: i2c-1, i2c-3
```

### 2. Install System Dependencies

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y \
    python3-rpi-lgpio \
    python3-spidev \
    python3-smbus2 \
    python3-pil \
    python3-numpy \
    python3-gpiozero \
    libraspberrypi-bin \
    pulseaudio \
    alsa-utils
```

### 3. Create Virtual Environment (PEP 668 Compliance)

```bash
python3 -m venv /opt/touchscreen-venv --system-site-packages
source /opt/touchscreen-venv/bin/activate
pip install luma.lcd requests numpy
```

### 4. Deploy WM8960 Driver

```bash
# Copy custom dtbo:
sudo cp roles/system/files/wm8960-audio-card.dts /boot/firmware/overlays/
sudo dtc -@ -I dts -O dtb -o /boot/firmware/overlays/wm8960-audio-card.dtbo \
         /boot/firmware/overlays/wm8960-audio-card.dts

# Enable in /boot/firmware/config.txt:
dtoverlay=wm8960-audio-card

# Reboot and verify:
arecord -l  # Should list WM8960
aplay -l    # Should list WM8960
```

### 5. Register Systemd Services

```bash
# For touchscreen:
sudo cp roles/touchscreen/templates/ts.service.j2 /etc/systemd/system/touchscreen.service
sudo systemctl daemon-reload
sudo systemctl enable --now touchscreen.service

# For voice assistant (if using):
sudo cp roles/voiceassistant/templates/lva.service.j2 /etc/systemd/system/lva.service
sudo systemctl enable --now lva.service
```

---

## ❓ Troubleshooting & FAQ

### **Deployment Issues**

**Q: `Permission denied (publickey)` during Ansible deployment?**

A: SSH key authentication isn't set up. Fix:
```bash
# On control machine:
ssh-copy-id -i ~/.ssh/id_rsa pi@<rpi-ip>
# Enter password: raspberry (default)

# Verify:
ssh -i ~/.ssh/id_rsa pi@<rpi-ip> "whoami"
# Output: pi
```

**Q: Playbook fails halfway. Can I re-run it?**

A: Yes! Ansible playbooks are **idempotent**. Re-running is safe:
```bash
ansible-playbook -i inventory/hosts.ini site.yml
# Will skip already-completed tasks
# Resume from the failure point
```

**Q: How do I check deployment progress?**

A: Watch logs in real-time:
```bash
# On RPi:
ssh player@<rpi-ip> "sudo journalctl -u touchscreen.service -f"
```

---

### **Hardware Issues**

**Q: Touchscreen is black / won't light up?**

A:
1. **Check SPI is enabled:**
   ```bash
   ls /dev/spidev0.0
   # Should exist, else run raspi-config → I4 SPI
   ```

2. **Check pin connections:** Verify physical wires match pinout table. Common mistakes:
   - LCD_CS (PIN 24) → GPIO 8? (Not GPIO 7)
   - LCD_DC (PIN 22) → GPIO 25?

3. **Run diagnostic:**
   ```bash
   ssh player@<rpi-ip>
   cd /opt/touchscreen-ui
   python3 test_screen.py
   # Displays color bars, touch sensitivity test
   ```

4. **Check backlight GPIO:**
   ```bash
   # Should see PWM output on GPIO 13:
   ls /sys/class/pwm/pwmchip0/pwm1/
   # If missing, backlight config in /boot/firmware/config.txt is wrong
   ```

---

**Q: WM8960 has noise / no audio output?**

A:
1. **Verify audio is reaching WM8960:**
   ```bash
   aplay -l
   # Should list: card 1: audio [WM8960 Audio Board]
   
   speaker-test -D plughw:1 -c 2 -t wav
   # Listen for test tone
   ```

2. **Check I2C control:**
   ```bash
   i2cdetect -y 1
   # Should see: 1a (WM8960 control address)
   ```

3. **Verify I2S clock:**
   ```bash
   sudo dmesg | grep wm8960
   # Should show clock rate: 12.288 MHz (NOT 24 MHz) due to clock doubling
   ```

4. **Check ALSA mixer:**
   ```bash
   alsamixer -c 1
   # Increase Output playback volumes
   ```

---

### **Software Issues**

**Q: Python ImportError: No module named 'spidev'?**

A: Virtual environment not activated. Fix:
```bash
source /opt/touchscreen-venv/bin/activate
python3 -c "import spidev; print('OK')"
```

Or install globally (not recommended on PEP 668 systems):
```bash
pip3 install --break-system-packages spidev
```

---

**Q: Voice assistant not responding?**

A:
1. **Check LVA is running:**
   ```bash
   sudo systemctl status lva.service
   ```

2. **Check microphone input:**
   ```bash
   arecord -D plughw:1 -f S16_LE -r 16000 - | aplay
   # Record then play back
   ```

3. **Check UDP listener:**
   ```bash
   ss -ulnp | grep 10701
   # Should see Python process listening on port 10701
   ```

4. **Check logs:**
   ```bash
   sudo journalctl -u lva.service -n 50
   ```

---

### **Performance Issues**

**Q: UI is laggy / touchscreen response slow?**

A:
1. **Check SPI frequency:**
   ```bash
   cat /opt/touchscreen-ui/ts.ini | grep spi_speed
   # Should be: 24000000 (24 MHz)
   ```

2. **Check for interference:**
   ```bash
   # Reduce SPI speed to test:
   nano /opt/touchscreen-ui/ts.ini
   # spi_speed = 12000000  (try 12 MHz)
   sudo systemctl restart touchscreen.service
   ```

3. **Check CPU load:**
   ```bash
   top
   # If python3 > 50%, UI loop is being preempted
   # Increase SCHED priority in main.py
   ```

---

### **FAQ: General Questions**

**Q: Can I use this with Raspberry Pi 5?**

A: Untested. RPi 5 has different GPIO mapper and faster CPU. You're welcome to test and report!

**Q: How do I update the touchscreen UI?**

A: Pull latest from GitHub, restart service:
```bash
ssh player@<rpi-ip>
cd /opt/touchscreen-ui
git pull origin main
sudo systemctl restart touchscreen.service
```

**Q: How do I backup my configuration?**

A: All state is in config files:
```bash
scp -r player@<rpi-ip>:/opt/touchscreen-ui/ui_config.toml ./
# Restore later: scp ui_config.toml player@<rpi-ip>:/opt/touchscreen-ui/
```

**Q: How do I add a new audio source (e.g., Spotify)?**

A: Modify PipeWire config:
```bash
ssh player@<rpi-ip>
sudo nano /etc/pipewire/pipewire.conf
# Add new source input rule
sudo systemctl restart pipewire.service
```

See [PipeWire Documentation](https://docs.pipewire.org/).

---

## 🏛️ Architecture Decisions

### ADR-001: Ansible vs Docker vs Shell Scripts

**Status:** Approved

**Context:** Raspberry Pi media player requires hardware interface management (dtoverlay, I2C/SPI configuration).

**Decision:** Use Ansible playbooks for infrastructure-as-code.

**Rationale:**
- **Scripts:** Hardware device trees (`dtoverlay`) difficult to version-control and re-deploy
- **Docker:** Audio/I2C hardware access adds complexity; isolation overhead negates resource savings
- **Ansible:** Declarative, idempotent, community support for RPi modules

**Trade-off:** Steeper learning curve vs long-term maintainability. **Maintainability wins.**

---

### ADR-002: PipeWire vs PulseAudio vs ALSA

**Status:** Approved

**Context:** Three audio sources (AirPlay, Bluetooth, Squeezelite) must mix seamlessly.

**Decision:** Use PipeWire as the core audio router.

**Rationale:**
- **ALSA:** Low-level; manual mixing adds complexity, poor Bluetooth integration
- **PulseAudio:** Reliable but complex configuration for multi-source, higher latency
- **PipeWire:** Modern architecture (2022+), native multi-source handling, lower latency

**Trade-off:** PipeWire is newer (Trixie exclusive) vs battle-tested PA. **Performance wins.**

---

### ADR-003: LVA vs wyoming-satellite

**Status:** Approved (after rejected wyoming)

**Context:** Voice control for Home Assistant smart home integration.

**Decision:** Use LVA (Linux Voice Assistant) + Sherpa-ONNX for offline speech recognition.

**Rationale:**
- **wyoming-satellite:** Protocol race conditions (ping/pong), Whisper hallucination on ARM, projects archived
- **LVA:** Stable connection (ESPHome native API), actively maintained (OHF), Sherpa-ONNX has ONNX quantization

**Trade-off:** Code patching (UDP injection) vs upstream compatibility. **Stability wins.**

See [Wyoming Evaluation Document](documents/VOICE_ASSISTANT_EVALUATION.md) for detailed analysis.

---

### ADR-004: Polling vs Interrupt-Driven Touch

**Status:** Approved

**Context:** FT6336U touch controller with I2C interface.

**Decision:** Pure polling mode (no interrupt pin).

**Rationale:**
- **Interrupt mode:** Requires INT pin → GPIO conflict with other peripherals; race conditions in high-speed UI
- **Polling mode:** CPU cost minimal (smbus2 I2C-3 isolated), predictable latency, easier debugging

**Trade-off:** ~1-2% CPU overhead vs GPIO resource contention. **Simplicity wins.**

---

## 🤝 Contributing

Contributions welcome! 

---

## 📄 License

MIT License — Free to modify, distribute, and use commercially. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Waveshare** for excellent hardware + documentation
- **Home Assistant** community for LVA + Sherpa-ONNX integration
- **Linux kernel** maintainers for device tree overlay support

**Made with ❤️ for the maker community.**

---

## 📚 Further Reading

- [WM8960 Technical Deep Dive](documents/WM8960/RECORD.md)
- [Voice Assistant Architecture](VOICE_ASSISTANT_HA.md)
- [Bluetooth Troubleshooting Guide](documents/BLUETOOTH_TIPS.md)
- [Raspberry Pi Pinout Reference](https://pinout.xyz/)
- [PipeWire Documentation](https://docs.pipewire.org/)

---

## 📞 Get Help

- **Issues:** [GitHub Issues](https://github.com/holefrog/Ansible_RPI_Touch/issues)
- **Discussions:** [GitHub Discussions](https://github.com/holefrog/Ansible_RPI_Touch/discussions)
- **Email:** contact at project email (if provided)

**Happy hacking! 🚀**
