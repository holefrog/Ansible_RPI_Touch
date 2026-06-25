# 智能语音助手知识库
# Linux Voice Assistant (LVA) + ESPHome API + Home Assistant + Raspberry Pi 4B

> 本文档是部署和维护本地离线语音助手系统的完整参考。按内容域分章，供 AI 按需取用。

---

## 目录

1. [系统概述与设计哲学](#1-系统概述与设计哲学)
2. [硬件约束与破局思路](#2-硬件约束与破局思路)
3. [系统架构与数据流](#3-系统架构与数据流)
4. [后台服务配置参考](#4-后台服务配置参考)
5. [音频底层架构](#5-音频底层架构)
6. [Home Assistant 接入与配置](#6-home-assistant-接入与配置)
7. [中文语义与意图配置](#7-中文语义与意图配置)
8. [UI 层集成](#8-ui-层集成)
9. [已知问题与根因分析](#9-已知问题与根因分析)
10. [日志查阅与时序排查法](#10-日志查阅与时序排查法)
11. [网络与系统稳定性](#11-网络与系统稳定性)
12. [媒体播放器联动](#12-媒体播放器联动)

---

## 1. 系统概述与设计哲学

### 目标

在树莓派触摸屏音乐播放器（CPU 占用约 10%，UI 帧率 18 FPS）上，无缝融合一个智能语音助手，同时满足：

- **0 隐私泄露**：全离线，不连接任何外部 AI 服务
- **0 日常额外功耗**：待机时 CPU 增量 < 2%
- **不牺牲 UI 体验**：语音推理期间屏幕和音频不卡顿
- **不依赖高性能服务器或独立显卡**

### 核心设计原则

> **"唤醒词触发时立刻暂停音乐——树莓派 CPU 彻底解放，就算瞬间满载也不会有任何卡顿。"**

这一思路彻底绕开了 AEC（回声消除）的需求，是整个架构的基石。

### 运行环境

| 组件 | 规格 |
|------|------|
| 边缘计算节点 | Raspberry Pi 4B（Cortex-A72，ARM NEON 向量加速）|
| 显示 | Waveshare 3.5寸 ST7796S 触摸屏 |
| 音频硬件 | WM8960 音频板（I2S，hw:0，S32_LE，48kHz 立体声）|
| Home Assistant | QNAP 453Bmini 虚拟机，IP `192.168.50.236:8123` |
| 树莓派 IP | `192.168.50.207` |
| 部署方式 | Ansible（用户级 Systemd 服务，`player` 用户，`roles/voiceassistant`）|

---

## 2. 硬件约束与破局思路

### 三大死结

#### 死结 1：AEC 带来的空载损耗

软件回声消除（AEC）在播放音乐时过滤喇叭声，代价是待机 CPU 占用激增 20%+，引起发热和功耗问题。**结论：放弃 AEC。**

#### 死结 2：HA 后端算力不足（J3455 的硬伤）

Home Assistant 运行在 J3455 虚拟机上。J3455 虽是 x86，但**硬件阉割了 AVX/AVX2 向量指令集**，AI 矩阵运算极慢。实测 Whisper 处理一句极短指令需卡顿 5～10 秒。**结论：STT/TTS 必须留在树莓派本地，不能交给 HA 虚拟机。**

#### 死结 3：前端 RPi 算力被 UI 和音频抢占

树莓派满负荷推理时 CPU 达 100%，UI 的 SPI 通信线程和音频解码线程会被饿死，导致屏幕冻结和喇叭爆音。**结论：推理期间必须先停止音乐播放。**

### 破局方案："暂停→推理→恢复"循环

```
日常待机        唤醒拦截              算力燃烧              收尾
OpenWakeWord →  检测到 "ok_nabu"  →  暂停音乐            →  播报完毕
1~2% CPU        发 awake 信号         CPU 全核推理 STT/TTS   发 done 信号恢复
                弹出语音蒙版           无任何线程被饿死        蒙版消失
```

---

## 3. 系统架构与数据流

### 架构选型历史：从 Wyoming Satellite 到 LVA

#### 旧架构（已废弃）：wyoming-satellite

旧架构以 `wyoming-satellite` 作为卫星端核心，通过 Wyoming 协议连接 HA。

**致命缺陷："2 秒必断"连接层 bug。**

具体表现为：satellite 启动后连接 HA，约 2 秒内必然出现：

```
WARNING:root:Did not receive ping response within timeout
INFO:root:Disconnected from server
```

**根因：** Wyoming 协议在 HA 侧和 satellite 侧之间存在 ping/pong 超时机制，两侧的时序存在竞争条件。这是 wyoming-satellite 项目的协议层 bug，与 VAD 配置、源码补丁、网络质量均无关。

**尝试过的无效手段：**
- 修改 `--ping-timeout` 参数——无效，HA 侧超时逻辑不受控
- 魔改 `satellite.py` 源码，加入 stealth VAD 延迟连接——解决了"必须 2 秒内开口"的体验问题，但无法解决连接层 ping 超时
- 关注上游 issue——社区大量同类报告，官方无修复计划

**最终裁定：** `wyoming-satellite` 已于 **2026 年 1 月 27 日被官方归档（archived/read-only）**，官方明确声明以 Linux Voice Assistant（LVA）取代，不再接受 PR 或 issue。继续在死亡项目上打补丁没有出路。

#### 新架构（现行）：Linux Voice Assistant (LVA)

LVA 由 Open Home Foundation（OHF）开发，**完全抛弃 Wyoming 协议**，改用 **ESPHome 原生 API** 与 HA 通信。ESPHome API 是成熟的双向流式协议，连接稳定性从根本上解决了 ping 超时问题。

**STT/TTS 不压在 HA 上：** LVA 只负责音频采集、唤醒词检测和音频流传输；STT/TTS 推理仍在树莓派本地的 sherpa-onnx 进程中运行，HA 通过 Wyoming Integration 调用它们，LVA 对此无感知。

### 组件端口总览

| 服务 | 端口 | 角色 |
|------|------|------|
| `lva`（linux-voice-assistant）| ESPHome API | 卫星端，采集音频 + 唤醒词检测（ok_nabu）|
| `wyoming-stt`（sherpa-onnx）| 10300 | 本地 STT（SenseVoice-int8），HA 调用 |
| `wyoming-tts`（sherpa-onnx）| 10200 | 本地 TTS（Matcha-Icefall + Vocos），HA 调用 |
| UDP 钩子（UI 信号）| 10701 | LVA event scripts → Python UI 的事件通道 |

### 完整数据流

```
麦克风（PipeWire，PULSE_SERVER）
    ↓
lva（linux-voice-assistant）
    ├─ 本地 OpenWakeWord 持续监听 "ok_nabu"
    │   检测到后 → 执行 LVA_ON_WAKE_WORD 脚本
    │                ↓
    │           awake.sh → UDP 10701
    │                ↓
    │           assistant_listener.py → main.py
    │                ↓
    │           暂停 Squeezelite + 弹出语音蒙版
    │
    └─ 唤醒后：通过 ESPHome API 将音频流推送给 HA
               HA Assist Pipeline 接管：
                 ├── VAD 判断录音结束
                 ├── 音频 → Wyoming Integration → sherpa-onnx STT（10300）推理
                 ├── 文字 → HA 意图解析（custom_sentences）
                 └── 回复文字 → Wyoming Integration → sherpa-onnx TTS（10200）合成
               HA 将 TTS 音频流回推给 LVA
               LVA 通过 PipeWire 播放
               LVA 执行 LVA_ON_TTS_END 脚本 → done.sh → UDP 10701
               main.py → 恢复 Squeezelite + 关闭蒙版
```

### 引擎选型说明

**为什么用 Sherpa-ONNX 而不是 Whisper + Piper：**

| 对比项 | Whisper（已弃用）| Sherpa-ONNX（现用）|
|--------|-----------------|-------------------|
| 架构 | 自回归 Decoder | Transducer / CTC（SenseVoice）|
| 静音/噪音处理 | 触发幻觉死循环，耗时 2+ 分钟 | 架构上不存在此问题 |
| TTS | Piper（Python，依赖复杂）| Matcha-Icefall + Vocos（纯 C++）|
| 依赖 | Python 依赖地狱 | 纯 C++ 内核，无依赖问题 |
| 内存驻留 | 否 | STT 模型全量驻留内存，无磁盘 I/O |

**为什么用 OpenWakeWord 而不是 Porcupine：**

| 对比项 | Porcupine v1（已弃用）| OpenWakeWord（现用）|
|--------|----------------------|---------------------|
| 唤醒词 | bumblebee（LVA 不内置）| ok_nabu（LVA 原生支持）|
| API Key | v1 不需要，但 v2+ 需要 | 完全开源，无 key |
| 与 LVA 集成 | 不支持，需要独立 wyoming 服务 | LVA 内置，零配置 |
| 维护状态 | 第三方集成，随 LVA 迭代可能失效 | 官方一等公民 |

---

## 4. 后台服务配置参考

> 所有服务均部署为**用户级 Systemd 服务**（`player` 用户），通过 Ansible 的 `roles/voiceassistant` 管理。

### Ansible Role 结构

```
roles/voiceassistant/
├── defaults/main.yml        # 所有可覆盖变量（路径、端口、唤醒词等）
├── handlers/main.yml        # restart wyoming-stt / wyoming-tts / lva
├── tasks/
│   ├── main.yml             # import 顺序：setup → stt → tts → lva → service
│   ├── setup.yml            # apt 依赖 + git clone LVA + script/setup 编译
│   ├── stt.yml              # sherpa-onnx STT venv + 模型下载 + service
│   ├── tts.yml              # sherpa-onnx TTS venv + 模型下载 + service
│   ├── lva.yml              # event scripts 部署 + lva.env + lva.service
│   └── service.yml          # systemd enable + start
├── templates/
│   ├── wyoming-stt.service.j2
│   ├── wyoming-tts.service.j2
│   ├── lva.service.j2       # ExecStart 指向 docker-entrypoint.sh（官方 bare metal 方案）
│   ├── lva.env.j2           # 所有 LVA 环境变量（HA token、唤醒词、PipeWire socket）
│   ├── awake.sh.j2          # → UDP 10701 {"event": "awake"}
│   ├── done.sh.j2           # → UDP 10701 {"event": "done"}
│   ├── transcript.sh.j2     # → UDP 10701 {"event": "transcript", "text": "..."}
│   ├── tts-start.sh.j2      # → UDP 10701 {"event": "tts-start"}
│   └── synthesize.sh.j2     # → UDP 10701 {"event": "synthesize", "text": "..."}
└── files/
    ├── sherpa_stt_server.py
    └── sherpa_tts_server.py
```

### LVA 安装方式说明（Bare Metal）

LVA 官方对非 Docker 安装的标准流程：

1. `git clone` 源码到 `/home/player/voiceassistant/linux-voice-assistant`
2. 执行 `script/setup --cxxflags="-O1 -g0" --makeflags="-j4"` 构建 `.venv` 并下载 OWW 模型
   （RPi 4B 首次编译约 5～10 分钟）
3. systemd service 的 `ExecStart` 直接指向仓库内的 `docker-entrypoint.sh`

> **官方说明：** LVA 在 bare metal 安装中复用 `docker-entrypoint.sh` 作为启动入口，不涉及任何 Docker 容器。通过 `EnvironmentFile` 注入的环境变量控制所有行为（HA 地址、唤醒词、PipeWire socket 路径、event 脚本路径等）。

### lva.service 关键配置

```ini
[Unit]
Description=Linux Voice Assistant (LVA) - ESPHome satellite for Home Assistant
After=network-online.target pipewire.service pipewire-pulse.service
Wants=network-online.target

[Service]
WorkingDirectory=/home/player/voiceassistant/linux-voice-assistant
ExecStart=/home/player/voiceassistant/linux-voice-assistant/docker-entrypoint.sh
EnvironmentFile=/home/player/voiceassistant/linux-voice-assistant/lva.env
Restart=always
RestartSec=5
```

### lva.env 关键环境变量

| 变量 | 示例值 | 说明 |
|------|--------|------|
| `HA_HOST` | `192.168.50.236` | HA 局域网 IP（非 Tailscale）|
| `HA_PORT` | `8123` | HA 端口 |
| `HA_TOKEN` | `（长期访问令牌）` | 在 HA 用户页面生成，存入 Ansible vault |
| `WAKEWORD` | `ok_nabu` | LVA 内置 OWW 模型名称 |
| `PULSE_SERVER` | `unix:/run/user/1000/pulse/native` | PipeWire Pulse socket |
| `XDG_RUNTIME_DIR` | `/run/user/1000` | 用户运行时目录 |
| `LVA_ON_WAKE_WORD` | `…/event_scripts/awake.sh` | 唤醒回调 |
| `LVA_ON_STT_END` | `…/event_scripts/transcript.sh` | 识别完成回调 |
| `LVA_ON_TTS_START` | `…/event_scripts/tts-start.sh` | TTS 开始回调 |
| `LVA_ON_TTS_END` | `…/event_scripts/done.sh` | TTS 结束回调 |

> **待验证：** lva.env 中的事件回调变量名（`LVA_ON_WAKE_WORD` 等）需在 RPi 上线后对照 `docker-entrypoint.sh` 实际变量名核对，名称错误会导致 event scripts 静默不执行，UI 无法感知语音状态。

### sherpa-onnx-stt 注意事项

- STT 模型（SenseVoice-int8）**全量驻留内存**，启动后无磁盘 I/O
- 底层为 CTC/Transducer 架构，从根本上不会产生自回归幻觉死循环
- 监听端口 10300，HA 通过 Wyoming Integration 调用

### sherpa-onnx-tts 注意事项

- 模型：Matcha-Icefall-zh-baker + hifigan_v2 vocoder
- 监听端口 10200，HA 通过 Wyoming Integration 调用
- 输出采样率 22050Hz，PipeWire 负责格式协商，无需在 LVA 侧硬编码

---

## 5. 音频底层架构

### 核心原则：全面使用 PipeWire，禁止直连 ALSA

| 方向 | 正确方式 | 禁止方式 | 禁止原因 |
|------|---------|---------|---------| 
| 录音（麦克风）| LVA 通过 `PULSE_SERVER` 调用 PipeWire | `arecord -D hw:0 ...` | 霸占底层 ALSA 通道，导致 PipeWire 挂起，Squeezelite 无声 |
| 录音（旧方案）| — | `arecord -D plughw:0 ...` | 在 WM8960 上产生白噪音，永远不要使用 |
| 播放（TTS 输出）| LVA 通过 PipeWire 混音输出 | `aplay -D plughw:0` | 独占声卡，与播放器冲突 |

### WM8960 硬件参数

```
接口：I2S
ALSA 设备：hw:0
格式：S32_LE
采样率：48kHz 立体声
```

PipeWire 自动接管 WM8960 并负责格式协商，LVA/sherpa-onnx 只需通过 PulseAudio 兼容层请求目标格式，PipeWire 完成转换。

### 麦克风增益配置

**不要在链路中加 `sox -v 0.5` 衰减输入信号。** 衰减本地信号会让 HA 端 Auto Gain 暴力放大远场杂音，导致 VAD 无法截断，引起 30 秒卡死死锁。

正确配置：
- 本地：保持原始拾音，不做衰减
- HA 端：**关闭 Auto Gain**
- HA 端：**Noise Suppression Level 设为 High / Maximum**

### 音频处理链（当前版本）

```
WM8960 麦克风（hw:0，S32_LE，48kHz）
    ↓
PipeWire 自动接管
    ↓
LVA 通过 PULSE_SERVER 请求 16kHz/S16LE/单声道，PipeWire 负责格式协商转换
    ↓
ESPHome API → HA Assist Pipeline → sherpa-onnx STT（10300）
```

---

## 6. Home Assistant 接入与配置

### 步骤 0：部署前的必要准备 (Token 凭证)
LVA 卫星端需要长期的 HA 访问凭证才能通过 ESPHome API 完成鉴权注册。
1. 登录 Home Assistant Web 界面。
2. 点击左下角你的用户名（个人资料），进入 **安全** 选项卡。
3. 滚动到最底部，在 **长期访问令牌 (Long-Lived Access Tokens)** 中点击“创建令牌”，命名为 `Linux Voice Assistant`。
4. 复制生成的长串 Token。
5. 返回你的 Ansible 项目，打开 `ansible/group_vars/all.yml` (或你的加密 vault)，添加变量：
   ```yaml
   lva_ha_token: "eyJh..." # 在这里粘贴你的超长token
   ```
> **注意：** 必须在 Ansible 部署前配置此 Token，否则 LVA 服务启动后会因 401 Unauthorized 鉴权失败而无限重连。

### 重要警告：忽略 ESPHome Voice Satellite 自动发现向导

LVA 通过 ESPHome API 接入后，HA 会自动发现该设备并弹出配置向导。**按需配置，不要选择"Full local processing"**（会在 J3455 虚拟机部署笨重插件，导致卡顿瘫痪）。

### 步骤 1：添加 Wyoming Integration（两次，用于 STT/TTS）

进入**配置 → 设备与服务 → 添加集成**，搜索 **Wyoming Protocol**，依次添加：

| 添加次序 | 角色 | 主机 | 端口 |
|---------|------|------|------|
| 1 | STT（大脑）| `192.168.50.207` | `10300` |
| 2 | TTS（嘴巴）| `192.168.50.207` | `10200` |

> LVA 卫星设备本身通过 ESPHome Integration 自动注册，无需手动添加 10700 端口。

### 步骤 2：防截断参数调整（关键）

在对应设备设置界面修改：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| Finished speaking detection | **Relaxed（宽松）** | 防止说话中途停顿被切断 |
| Auto gain | **关闭** | 防止放大远场杂音导致 VAD 死锁 |
| Noise suppression level | **High / Maximum** | 抑制背景噪音 |

### 步骤 3：组装语音助手 Pipeline

进入**配置 → 语音助手 → 添加助手**：

| 字段 | 值 |
|------|-----|
| 名称 | Raspberry Pi Local Edge |
| 语言 | 中文 (Chinese) |
| 对话代理 | Home Assistant |
| STT | 刚添加的 Sherpa-ONNX（10300）|
| TTS | 刚添加的 Sherpa-ONNX（10200）|
| 唤醒词 | （留空，LVA 本地 OWW 已代劳）|

创建后，点击助手右上角三个点 → **设为默认**（旁边会出现五角星）。

### 步骤 4：将 LVA 设备关联至此 Pipeline

在 ESPHome 集成的 LVA 设备页面，将其使用的语音助手指向上一步创建的 Pipeline。

---

## 7. 中文语义与意图配置

### 问题背景

HA 默认的中文分词会把"关上客厅灯"错误切分为"上客厅"，导致设备控制失败。此外，"现在几点了"这类问句 HA 原生不支持。

### 解决方案：custom_sentences + intent_script

**文件位置：** HA config 目录下的 `custom_sentences/zh/custom.yaml`

```yaml
language: "zh"
intents:
  GetTimeIntent:
    data:
      - sentences:
          - "现在几点[了]"
          - "几点了"
          - "[告诉][我]时间"

  HassTurnOn:
    data:
      - sentences:
          - "打开{name}[的]灯"
          - "开{name}灯"

  HassTurnOff:
    data:
      - sentences:
          - "关[上|闭]{name}[的]灯"
          - "关{name}灯"
```

**`configuration.yaml` 中的意图响应：**

```yaml
intent_script:
  GetTimeIntent:
    speech:
      text: "现在是 {{ now().strftime('%p %I点%M分') | replace('AM', '上午') | replace('PM', '下午') }}"
```

**配置说明与适用范围：**
- `[上|闭]` 语法提供可选词，解决特定边界下的分词歧义。
- `{name}` 为槽位，自动捕获设备名称。**注意：这取决于 HA 中已暴露的实体列表，未暴露的设备无法被识别。**
- **为何不用内置意图：** HA 的 HassTurnOn/Off 内置意图本身支持中文，但对类似"关上客厅灯"这种高频错误边界（切分为"上客厅"）处理不佳。本方案并非通用的中文控制核心，而是针对已知中文分词 Bad Case 的定向补丁方案。
- `GetTimeIntent` 直接使用 Jinja2 读取本地系统时间，**全程离线，不调用任何外部 LLM**。

### 避坑指南（重大陷阱）

**💥 第一大坑：目录名与语言标签的“大小写暗杀”**
- **避坑核心：** `custom_sentences` 的目录名（如 `zh-CN`）和里面每一个 YAML 文件的 `language: "zh-CN"` 必须 100% 连大小写都绝对一致！
- **血泪教训：** 如果不一致，系统连个错误都不会报，只会静默忽略你的自定义配置。这会导致系统自带的内置 Intent 能用，而你的自定义指令全变哑巴，让你像无头苍蝇一样到处乱查代码，根本想不到是大小写出了错。

**💥 第二大坑：被系统强行覆盖的 `action_response`**
- **避坑核心：** 在 `intent_script` 的 `speech`（播报）模块中，永远只能用 `action_response` 这个内置变量来获取数据。
- **血泪教训：** 无论你在前一步的 action 动作里怎么自定义返回值（比如写了 `response_variable: forecast_data`），当数据流转到 speech 播报阶段时，HA 都会极其霸道地把它没收，并强制改名为 `action_response`。如果你还在傻傻地用自己定义的变量名，系统立马就会报错崩溃。

**💥 第三大坑：深夜天气 API 的“时空错乱”**
- **避坑核心：** 深夜查天气时，今天的数据可能会被 API 删掉导致数组错位。绝对不要用“数组第 1 个”来代表今天，必须写代码用“年月日”字符串去精确匹配 `datetime` 字段。

**💥 第四大坑：中文量词的灾难级提取（5分钟变5秒）**
- **避坑核心：** 时间槽位必须拆分为 `{hours}`、`{minutes}`、`{seconds}`，并在 `lists` 里声明 `wildcard` 通配符。最后在执行脚本里，必须用数学公式 `h*3600 + m*60 + s` 统一折算成秒数再传给定时器。

**💥 第五大坑：自定义语音的“身首异处”**
- **避坑核心：** “听觉”（中文句子定义）必须单独放在 `custom_sentences` 目录里；“动作”（怎么执行、怎么播报）必须单独放在主配置的 `intent_script` 里。这两者绝对不能写在一起。
---

## 8. UI 层集成

### 信号通道

- `assistant_listener.py`：监听本机 **10701** UDP 端口，接收 LVA event scripts 发出的事件信号
- 信号类型：`awake`（唤醒）、`transcript`（识别结果）、`tts-start`（TTS 开始）、`done`（完成）

### 状态与超时配置

| 状态 | 超时配置 | 说明 |
|------|---------|------|
| `awake` 兜底超时 | **8.0 秒** | HA 静默挂断时触发兜底 timeout，屏幕迅速复位 |
| 指令窗口 | **10 秒** | 唤醒后用户下达指令的最大等待时间 |
| 助手界面关闭 | **0 秒（立即退出）** | 收到 `done` 信号时 UI 瞬间清空对话、退出蒙版并恢复音乐 |

### 已知 UI Bug 及修复

**气泡滚动消失问题：**
多次对话后，HA 回复气泡在屏幕上"消失"。根因是坐标算法错误。

修复：在 `ui_screen_assistant.py` 中将坐标算法改为：
```python
cy = min(CHAT_TOP, CHAT_BOT - total_h)
```
确保历史记录始终自底向上对齐，不会超出屏幕边界。

---

## 9. 已知问题与根因分析

### 问题一：wyoming-satellite "2 秒必断"（已通过换架构根治）

**现象：** wyoming-satellite 启动后约 2 秒，日志出现：
```
WARNING:root:Did not receive ping response within timeout
INFO:root:Disconnected from server
```
随后反复重连，功能性断路。社区从 2024 年起大量同类报告。

**根因：** Wyoming 协议的 ping/pong 超时机制在 HA 侧和 satellite 侧之间存在时序竞争，是协议层 bug。与 VAD 参数、源码补丁、网络质量无关。

**尝试过的无效手段：**
- 修改 `--ping-timeout` 参数
- 魔改 `satellite.py`，加入 stealth VAD 延迟连接（该补丁解决了"必须 2 秒内开口"的体验问题，但无法触及连接层）
- 上游已归档，无修复计划

**根治方案：** 放弃 wyoming-satellite，迁移至 LVA（ESPHome API），连接层从协议上消除了此问题。

---

### 问题二：STT 幻觉死循环（Whisper 专属，已通过换引擎解决）

**现象：** 纯噪音或静音的 3 秒音频，Whisper 需要 2 分 20 秒才能输出结果。

**根因：** Whisper 的自回归 Decoder 在找不到有效语音时，反复生成 `initial_prompt` 中的内容（如"打开小米台灯、关上小米台灯..."），ARM 上每步 50～100ms，循环数百步累计分钟级别。

**解决方案：** 替换为 Sherpa-ONNX（SenseVoice-int8），CTC 架构从根本上不存在此问题。

---

### 问题三：Squeezelite 进度条正常但无声音

**现象：** Squeezelite 显示进度条在走，但喇叭没有声音。

**根因：** `arecord -D hw:0` 直连 ALSA 霸占了声卡底层通道，PipeWire 试图接管声卡时抛出 `Device or resource busy`，声卡模块被挂起。

**解决方案：** 所有音频 I/O 均通过 PipeWire（LVA 使用 `PULSE_SERVER` 环境变量），不直连 ALSA。

---

### 问题四：麦克风死锁（30 秒卡顿）

**现象：** 远处电视杂音被清晰收录，语音助手卡死约 30 秒。

**根因（AGC 错位）：** 链路中加入 `sox -v 0.5` 衰减了音频信号，HA 端 Auto Gain 检测到微弱信号后暴力放大，将远场噪音放大至接近语音级别，导致 VAD 无法判断"说话结束"而持续录音直到全局超时。

**解决方案：**
1. 本地不做任何衰减
2. HA 端关闭 Auto Gain
3. HA 端 Noise Suppression 调至 High/Maximum

---

### 问题五：Piper TTS 无声音输出（历史，已换引擎）

**现象：** TTS 无声，HA 端 ffmpeg 转码报错。

**根因：** `ModuleNotFoundError: No module named 'unicode_rbnf'`。Piper 缺少此依赖导致中文 phonemize 失败，输出全是 0x00 的空 WAV 数据。

**根本解决：** 替换为 Sherpa-ONNX TTS（纯 C++，无此类依赖问题）。

---

### 问题六：Wi-Fi 休眠导致单向失联

**现象：** 树莓派本地音乐正常播放（出站 TCP 正常），但局域网其他设备 Ping 不通，SSH 报 `No route to host`。

**根因：** 树莓派 Wi-Fi 芯片进入 Power Save 模式，忽视入站 ARP 广播，但出站播放器 TCP 连接能反向唤醒芯片，造成"单向失联"假象。

**解决方案：** 修改 NetworkManager 配置，永久关闭 Wi-Fi 省电：

```ini
# /etc/NetworkManager/conf.d/wifi-powersave.conf
[connection]
wifi.powersave = 2
```

---

## 10. 日志查阅与时序排查法

### 重要前提：用户级服务

所有服务均为**用户级 Systemd 服务**，必须以 `player` 用户身份操作，**不能直接使用 `sudo systemctl`**。

```bash
# 正确
systemctl --user status lva
systemctl --user restart wyoming-stt

# 错误
sudo systemctl status lva
```

### 实时追踪日志

```bash
# 追踪单个服务
journalctl --user -u lva -f

# 同时追踪多个服务（按时间合并输出）
journalctl --user -u lva -u wyoming-stt -u wyoming-tts -f
```

### 查阅历史日志

```bash
# 过去 10 分钟
journalctl --user -u lva --since "10 minutes ago"

# 昨天的 STT 日志
journalctl --user -u wyoming-stt --since "yesterday"
```

### 无日志报错处理

若执行 `journalctl --user` 时提示 `No journal files were found.`：

**方案 A：持久化（推荐）**
```bash
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
sudo usermod -aG systemd-journal player
# 必须断开 SSH 重新登录后生效
```

**方案 B：Root 临时查看**
```bash
sudo journalctl \
  _SYSTEMD_USER_UNIT=lva.service \
  _SYSTEMD_USER_UNIT=wyoming-stt.service \
  _SYSTEMD_USER_UNIT=wyoming-tts.service \
  --since "5 minutes ago"
```

### 时序排查法（核心手段）

语音链路长，排查时不要靠感觉猜，直接比较各服务的时间戳：

```
链路：本地唤醒 → ESPHome API → HA VAD → 回传 STT → HA 意图解析 → 回传 TTS → PipeWire 播放

排查步骤：
1. 找 LVA 日志中 "wake word detected" 的时间戳 → T0（唤醒点）
2. 找 "STT 开始推理" 的时间戳 → T1
   T1 - T0 = ESPHome 流式录音 + HA VAD 判定 + Wyoming 回传耗时
3. 找 "STT 输出识别结果" 的时间戳 → T2
   T2 - T1 = STT 推理耗时
   若 > 10 秒，说明 STT 陷入异常
4. 找 "TTS 开始接收文字" 的时间戳 → T3
   T3 - T2 = HA 意图解析 + 网络耗时
5. 找 "TTS 生成完毕" 的时间戳 → T4
   找 "PipeWire 开始播放" 的时间戳 → T5
   T5 - T4 = 音频设备等待时间（若卡顿，检查 PipeWire 状态）
```

**黄金法则：哪个区间的秒数最多，那个模块就是瓶颈。**

---

## 11. 网络与系统稳定性

### Wi-Fi 省电关闭

参见第 9 章问题六。永久关闭树莓派 Wi-Fi Power Save，防止入站连接失联。

### HA 与树莓派的网络关系

- HA 虚拟机 IP：`192.168.50.236:8123`
- Tailscale **仅安装在 HA 虚拟机上**，局域网设备（包括树莓派）不可通过 Tailscale 访问 HA
- LVA 通过 `HA_HOST=192.168.50.236` 直连 HA，不经过 Tailscale

### 连接稳定性

LVA 使用 ESPHome API，该协议设计为长期稳定连接，无 Wyoming ping/pong 超时机制。连接中断时 LVA 自动重连（`RestartSec=5`），不影响整体功能。

---

## 12. 媒体播放器联动

### 语音控制本地 Squeezelite 播放器

利用 HA 的**区域感知（Area Awareness）**机制，无需编写代码实现语音媒体控制。

**配置步骤：**

1. **暴露播放器实体**
   进入 HA **设置 → 语音助手 → 暴露**，确保 `media_player.rpi_squeeze`（或对应实体名）对 Assist 可见。

2. **分配到同一区域**
   进入 HA **设置 → 区域与区域**，创建区域（如"桌面"），将 **LVA 设备**（ESPHome Integration 中）和 **Squeezelite 播放器实体**分配到**同一区域**。

**效果：** 对着树莓派说"暂停"、"下一首"、"音量调到百分之五十"，HA 自动匹配该区域内的 `media_player` 并下发指令，不影响 PipeWire 混音比例。

### 唤醒时的播放器控制流（Python 层）

```
sequenceDiagram
    autonumber
    participant Mic as 麦克风 (PipeWire)
    participant LVA as LVA (satellite.py)
    participant UI as Touchscreen UI
    participant HA as Home Assistant
    participant STT as Sherpa-ONNX (STT)
    participant TTS as Sherpa-ONNX (TTS)
    
    Note over Mic, LVA: 1. 待机状态
    Mic->>LVA: 源源不断地输入本地音频
    LVA->>LVA: OpenWakeWord 实时比对唤醒词
    
    Note over LVA, UI: 2. 触发唤醒 (Wake up)
    LVA->>LVA: 听到 "ok nabu"
    LVA->>UI: 运行 awake.sh -> UDP {"event": "awake"}
    UI->>UI: 屏幕显示“录音中/倾听”动画
    LVA->>HA: 通过 ESPHome API 请求 run_pipeline
    
    Note over LVA, STT: 3. 音频流式传输 & 识别
    LVA->>HA: 开始流式上传语音 ("打开客厅灯")
    HA->>STT: 路由语音流至 wyoming-stt
    STT->>STT: VAD 判定用户说话结束 (Relaxed)
    STT->>HA: 返回文本 "打开客厅灯"
    
    Note over HA, UI: 4. 识别完成 (Transcript)
    HA->>LVA: 返回 STT_END 事件 (含文本)
    LVA->>UI: 运行 transcript.sh -> UDP {"event": "transcript", "text": "打开客厅灯"}
    UI->>UI: 屏幕上刷出用户说的话
    
    Note over HA, HA: 5. 意图执行 (Intent)
    HA->>HA: NLU 匹配，执行“开灯”动作
    HA->>HA: 生成回答文本: "好的，已打开客厅灯"
    
    Note over HA, UI: 6. 语音合成与文字推送 (TTS Start / Synthesize)
    HA->>LVA: 返回 TTS_START 事件 (含回答文本)
    LVA->>UI: 运行 tts-start.sh -> UDP {"event": "tts-start"}
    LVA->>UI: 运行 synthesize.sh -> UDP {"event": "synthesize", "text": "好的，已打开客厅灯"}
    UI->>UI: 屏幕刷出助手回答的文字内容
    HA->>TTS: 请求 wyoming-tts 合成声音
    TTS->>HA: 返回音频数据
    
    Note over HA, LVA: 7. 音频播放
    HA->>LVA: 下发音频流
    LVA->>Mic: 通过 PipeWire 播放声音
    
    Note over LVA, UI: 8. 流程结束 (Done)
    LVA->>LVA: 播报结束
    LVA->>UI: 运行 done.sh -> UDP {"event": "done"}
    UI->>UI: 延时后，屏幕恢复时钟/音乐待机画面

```
