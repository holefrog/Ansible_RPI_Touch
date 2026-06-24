# 智能语音助手知识库
# Wyoming Protocol + Home Assistant + Raspberry Pi 4B

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
| 部署方式 | Ansible（用户级 Systemd 服务，`player` 用户）|

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
Porcupine  →  检测到 "Bumblebee"  →  暂停音乐            →  播报完毕
1~2% CPU      发 awake 信号          CPU 全核推理 STT/TTS   发 play 恢复
              弹出语音蒙版            无任何线程被饿死        蒙版消失
```

---

## 3. 系统架构与数据流

### 组件端口总览

| 服务 | 端口 | 角色 |
|------|------|------|
| `wyoming-porcupine1` | 10400 | 本地唤醒词检测（"Bumblebee"）|
| `sherpa-onnx-stt` | 10300 | 本地 STT（SenseVoice-int8）|
| `sherpa-onnx-tts` | 10200 | 本地 TTS（Matcha-Icefall + Vocos）|
| `wyoming-satellite` | 10700 | 大管家，串联录音/唤醒/HA |
| UDP 钩子（UI 信号）| 10701 | satellite → Python UI 的事件通道 |

### 完整数据流

```
麦克风（parec，PipeWire）
    ↓
wyoming-satellite（10700）
    ├─ 本地：wyoming-porcupine1（10400）持续监听唤醒词
    │        检测到 "Bumblebee" → 发 UDP 至 10701
    │                              ↓
    │                         assistant_listener.py
    │                              ↓
    │                         main.py → 暂停 Squeezelite + 弹出蒙版
    │
    └─ 唤醒后：连接 HA（192.168.50.236:8123）
               HA 端 VAD 判断录音结束
               音频回传 → sherpa-onnx-stt（10300）推理
               文字 → HA 意图解析（custom_sentences）
               回复文字 → sherpa-onnx-tts（10200）合成
               音频 → paplay（PipeWire 混音输出）
               Wyoming 发 done 信号 → satellite → UDP 10701
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

**为什么用 Porcupine v1：**
- C 语言编写，CPU 占用长期维持 1%～2%
- v1 版本**不需要 API Key**

---

## 4. 后台服务配置参考

> 所有服务均部署为**用户级 Systemd 服务**（`player` 用户），通过 Ansible 的 `satellite.yml` 管理。

### wyoming-satellite 关键启动参数

```bash
wyoming-satellite \
  --uri tcp://0.0.0.0:10700 \
  --mic-command "parec --raw --rate=16000 --channels=1 --format=s16le" \
  --mic-command-samples-per-chunk 512 \
  --snd-command "paplay --raw --rate=22050 --channels=1 --format=s16le" \
  --wake-uri tcp://localhost:10400 \
  --wake-word-name bumblebee \
  --awake-wav /path/to/awake_prompt.wav \
  --vad-wake-word-timeout 5
```

**关键参数说明：**

| 参数 | 值 | 说明 |
|------|----|------|
| `--mic-command` | `parec ...` | 使用 PipeWire，禁止使用 `arecord -D hw:0`（会死锁） |
| `--mic-command-samples-per-chunk` | `512` | **开启 VAD 时的硬性要求。** 默认值为 1024，但底层的 Silero VAD 引擎严格要求每帧包含 512 个采样点（1024 bytes）。若不设置此项，只要检测到语音就会触发 `InvalidChunkSizeError` 导致主进程崩溃。|
| `--snd-command` | `paplay ...` | 使用 PipeWire。**注意：此处的 `--rate=22050` 与当前 Matcha-Icefall 模型强绑定，若未来更换输出 24kHz 等其他格式的模型，此处必须同步修改。** |
| `--awake-wav` | 自定义音频文件 | 唤醒后的听觉反馈，与视觉蒙版同步 |
| `--vad-wake-word-timeout` | `5` | 唤醒后用户最长思考时间（秒），超时视为误唤醒 |

### VAD 本地魔改说明

**问题根源：** 原版 `wyoming-satellite` 在开启本地唤醒词后，**强制禁用** `--vad` 参数。导致唤醒后立刻连接 HA，用户必须在 HA 的 2 秒静音超时内抢答开口。

**解决方案：** 魔改树莓派本地的 `satellite.py` 源码。
- **魔改内容：** 重写了 `WakeStreamingSatellite` 类的事件处理逻辑。唤醒后进入 `waiting_for_vad` 状态，此时麦克风音频仅在本地 `pysilero_vad` 引擎中做缓冲区判定。一旦侦测到实体语音，才会将 `is_streaming` 设为 True 并连接 HA，同时将缓冲区内的"前半句话"上报。
- **持久化方案：** 为了防止上游升级或重装导致魔改代码丢失，该 patch 已整合进 Ansible 的 `roles/wyoming/tasks/satellite.yml` 中。在 `pip install` 之后，通过 Ansible `copy` 模块强制用我们预存的 `roles/wyoming/files/satellite.py` 覆盖官方文件。如果未来更换硬件或上游升级，仅需重新运行 playbook 即可自动打好补丁。

**工作流变更：** 唤醒后，satellite 进入"本地隐身监听模式"，等本地 VAD 引擎检测到用户真正开口，才建立 HA 连接，并携带缓冲区中的"前半句话"一并上传。用户有完整的 5 秒思考时间。

### sherpa-onnx-stt 注意事项

- STT 模型（SenseVoice-int8）**全量驻留内存**，启动后无磁盘 I/O
- 底层为 CTC/Transducer 架构，从根本上不会产生自回归幻觉死循环

### wyoming-porcupine1 注意事项

- 使用 **v1 版本**，无需 API Key
- 唤醒词固定为 `bumblebee`

---

## 5. 音频底层架构

### 核心原则：全面使用 PipeWire，禁止直连 ALSA

| 方向 | 正确命令 | 禁止命令 | 禁止原因 |
|------|---------|---------|---------|
| 录音（麦克风）| `parec --raw --rate=16000 --channels=1 --format=s16le` | `arecord -D hw:0 ...` | 霸占底层 ALSA 通道，导致 PipeWire 挂起，Squeezelite 无声 |
| 录音（旧方案）| — | `arecord -D plughw:0 ...` | 在 WM8960 上产生白噪音，永远不要使用 |
| 播放（TTS 输出）| `paplay --raw --rate=22050 --channels=1 --format=s16le` | `aplay -D plughw:0` | 独占声卡，与播放器冲突；`sox -v 3` 暴力放大易破音 |

### WM8960 硬件参数

```
接口：I2S
ALSA 设备：hw:0
格式：S32_LE
采样率：48kHz 立体声
```

### 麦克风增益配置

**不要使用 `sox -v 0.5` 衰减输入信号。** 衰减本地信号会让 HA 端的 Auto Gain 暴力放大远场杂音，导致 VAD 无法截断，引起 30 秒卡死死锁。

正确配置：
- 本地：**删除 `sox -v 0.5`**，恢复原始拾音
- HA 端：**关闭 Auto Gain**
- HA 端：**Noise Suppression Level 设为 High / Maximum**

### 音频处理链（正确版本）

```
WM8960 麦克风（hw:0，S32_LE，48kHz）
    ↓
PipeWire 自动接管
    ↓
parec 向 PipeWire 请求 16kHz/S16LE/单声道格式，由 PipeWire 负责格式协商转换并交付
（wyoming-satellite mic-command：`parec --raw --rate=16000 --channels=1 --format=s16le`）
    ↓
wyoming-satellite → HA → sherpa-onnx-stt
```

---

## 6. Home Assistant 接入与配置

### 重要警告：忽略自动发现弹窗

新版 HA 会自动发现 `wyoming-satellite` 并弹出 **Voice Satellite setup** 向导。**直接关闭，不要使用。** 误选"Full local processing"会在 J3455 虚拟机部署笨重插件，导致卡顿瘫痪。

### 步骤 1：手动添加 Wyoming 集成（三次）

进入 **配置 → 设备与服务 → 添加集成**，搜索 **Wyoming Protocol**，依次添加：

| 添加次序 | 角色 | 主机 | 端口 |
|---------|------|------|------|
| 1 | STT（大脑）| `192.168.50.207` | `10300` |
| 2 | TTS（嘴巴）| `192.168.50.207` | `10200` |
| 3 | Satellite（身体）| `192.168.50.207` | `10700` |

> 添加 10700 后 HA 会再次弹出 Voice Satellite setup 向导，点右上角 X 关闭即可。

### 步骤 2：防截断参数调整（关键）

在对应设备设置界面修改：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| Finished speaking detection | **Relaxed（宽松）** | 防止说话中途停顿被切断 |
| Auto gain | **关闭** | 防止云端放大远场杂音导致 VAD 死锁 |
| Noise suppression level | **High / Maximum** | 抑制背景噪音 |

### 步骤 3：组装语音助手

进入 **配置 → 语音助手 → 添加助手**：

| 字段 | 值 |
|------|----|
| 名称 | Raspberry Pi Local Edge |
| 语言 | 中文 (Chinese) |
| 对话代理 | Home Assistant |
| STT | 刚添加的 Sherpa-ONNX |
| TTS | 刚添加的 Sherpa-ONNX |
| 唤醒词 | （留空，本地 Porcupine 已代劳）|

创建后，点击助手右上角三个点 → **设为默认**（旁边会出现五角星）。

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

---

## 8. UI 层集成

### 信号通道

- `assistant_listener.py`：监听本机 **10701** UDP 端口，接收 satellite 发出的事件信号
- 信号类型：`awake`（唤醒）、`done`（完成）

### 状态与超时配置

| 状态 | 超时配置 | 说明 |
|------|---------|------|
| `awake` 兜底超时 | **8.0 秒** | HA 静默挂断（如无有效识别）时触发兜底 timeout 或 error 信号，屏幕迅速复位 |
| 指令窗口 | **10 秒** | 唤醒后用户下达指令的最大等待时间 |
| 助手界面关闭 | **0 秒（立即退出）** | 当 Wyoming 最终触发 `done` 信号时（此时代表 TTS 播报必然完毕，或任务完全终结），UI 会**瞬间清空对话、退出蒙版，并向播放器发送 play 恢复命令**。不再死等旧版的超时秒数，彻底避免与音乐恢复时序冲突。|

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

### 问题一：STT 幻觉死循环（Whisper 专属，已通过换引擎解决）

**现象：** 纯噪音或静音的 3 秒音频，Whisper 需要 2 分 20 秒才能输出结果。

**根因：** Whisper 的自回归 Decoder 在找不到有效语音时，反复生成 `initial_prompt` 中的内容（如"打开小米台灯、关上小米台灯..."），ARM 上每步 50～100ms，循环数百步累计分钟级别。

**解决方案：** 替换为 Sherpa-ONNX（SenseVoice-int8），CTC 架构从根本上不存在此问题。

> **若因特殊原因仍需使用 Whisper 的临时缓解措施：** 在 `wyoming-whisper.service` 的 ExecStart 中加上 `--vad-filter` 参数，让 Silero VAD 在推理前过滤静音段，耗时可从 2 分钟降到 < 1 秒。

---

### 问题二：Squeezelite 进度条正常但无声音

**现象：** Squeezelite 显示进度条在走，但喇叭没有声音。

**根因：** `arecord -D hw:0` 直连 ALSA 霸占了声卡底层通道，PipeWire 试图接管声卡时抛出 `Device or resource busy`，声卡模块被挂起。

**解决方案：** 将录音命令从 `arecord -D hw:0` 改为 `parec`（PipeWire 兼容层）。

---

### 问题三：麦克风死锁（30 秒卡顿）

**现象：** 远处电视杂音被清晰收录，语音助手卡死约 30 秒。

**根因（AGC 错位）：** 本地 `sox -v 0.5` 衰减了音频信号，HA 端 Auto Gain 检测到微弱信号后暴力放大，将远场噪音放大至接近语音级别，导致 VAD 无法判断"说话结束"而持续录音直到全局超时。

**解决方案：**
1. 删除本地 `sox -v 0.5`
2. HA 端关闭 Auto Gain
3. HA 端 Noise Suppression 调至 High/Maximum

---

### 问题四：Piper TTS 无声音输出

**现象：** TTS 无声，HA 端 ffmpeg 转码报错。

**根因：** `ModuleNotFoundError: No module named 'unicode_rbnf'`。Piper 缺少此依赖导致中文 phonemize 失败，输出全是 0x00 的空 WAV 数据。

**临时修复（历史参考）：**
```bash
ssh player@192.168.50.207
/home/player/wyoming/piper/bin/pip install unicode-rbnf
systemctl --user restart wyoming-piper
```

**根本解决：** 替换为 Sherpa-ONNX TTS（纯 C++，无此类依赖问题）。

---

### 问题五：Wi-Fi 休眠导致单向失联

**现象：** 树莓派本地音乐正常播放（出站 TCP 正常），但局域网其他设备 Ping 不通，SSH 报 `No route to host`。

**根因：** 树莓派 Wi-Fi 芯片进入 Power Save 模式，忽视入站 ARP 广播，但出站播放器 TCP 连接能反向唤醒芯片，造成"单向失联"假象。

**解决方案：** 修改 NetworkManager 配置，永久关闭 Wi-Fi 省电：

```ini
# /etc/NetworkManager/conf.d/wifi-powersave.conf
[connection]
wifi.powersave = 2
```

---

### 问题六：唤醒后必须抢答（2 秒内开口）

**现象：** 唤醒后如果不在 2 秒内开口，HA 直接切断连接当做误唤醒。

**根因：** 原版 `wyoming-satellite` 开启本地唤醒词后强制禁用 `--vad` 参数，唤醒后立刻连接 HA，受制于 HA 默认的短促静音超时。

**解决方案：** 魔改 `satellite.py` 源码（详见第 4 章），实现本地 VAD 延迟连接。

---

### 问题七：幽灵超时（唤醒后无响应卡 25 秒）

**现象：** 唤醒后没有说话，屏幕卡住等待 25 秒后报错。

**根因：** `awake` 状态的兜底超时设置过长（25 秒），HA 静默挂断后 UI 不知道，持续等待。

**解决方案：** 将 `awake` 兜底超时从 25.0 秒缩短至 **8.0 秒**。

---

## 10. 日志查阅与时序排查法

### 重要前提：用户级服务

所有 Wyoming 服务均为**用户级 Systemd 服务**，必须以 `player` 用户身份操作，**不能直接使用 `sudo systemctl`**。

```bash
# 正确
systemctl --user status wyoming-satellite
systemctl --user restart sherpa-onnx-stt

# 错误
sudo systemctl status wyoming-satellite
```

### 实时追踪日志

```bash
# 追踪单个服务
journalctl --user -u wyoming-satellite -f

# 同时追踪多个服务（按时间合并输出）
journalctl --user -u wyoming-satellite -u sherpa-onnx-stt -u sherpa-onnx-tts -f
```

### 查阅历史日志

```bash
# 过去 10 分钟
journalctl --user -u wyoming-satellite --since "10 minutes ago"

# 昨天的 STT 日志
journalctl --user -u sherpa-onnx-stt --since "yesterday"
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
  _SYSTEMD_USER_UNIT=wyoming-satellite.service \
  _SYSTEMD_USER_UNIT=sherpa-onnx-stt.service \
  _SYSTEMD_USER_UNIT=sherpa-onnx-tts.service \
  --since "5 minutes ago"
```

### 时序排查法（核心手段）

语音链路长，排查时不要靠感觉猜，直接比较各服务的时间戳：

```
链路：本地唤醒 → HA 录音 VAD → 回传 STT → HA 意图解析 → 回传 TTS → PipeWire 播放

排查步骤：
1. 找"Porcupine 检测到 bumblebee"的时间戳 → T0（唤醒点）
2. 找"STT 开始推理"的时间戳 → T1
   T1 - T0 = 流式录音 + HA VAD 判定 + 网络回传的耗时
3. 找"STT 输出识别结果"的时间戳 → T2
   T2 - T1 = STT 推理耗时
   若 > 10 秒，说明 STT 陷入异常（幻觉死循环或模型问题）
4. 找"TTS 开始接收文字"的时间戳 → T3
   T3 - T2 = HA 意图解析 + 网络耗时
5. 找"TTS 生成完毕"的时间戳 → T4
   找"paplay 开始播放"的时间戳 → T5
   T5 - T4 = 音频设备等待时间（若卡顿，检查 PipeWire 状态）
```

**黄金法则：哪个区间的秒数最多，那个模块就是瓶颈。**

---

## 11. 网络与系统稳定性

### Wi-Fi 省电关闭

参见第 9 章问题五。永久关闭树莓派 Wi-Fi Power Save，防止入站连接失联。

### HA 与树莓派的网络关系

- HA 虚拟机 IP：`192.168.50.236:8123`
- Tailscale **仅安装在 HA 虚拟机上**，局域网设备（包括树莓派）不可通过 Tailscale 访问 HA
- 局域网设备直接通过 `192.168.50.236` 访问 HA

### Satellite 轮询断连

HA 每 8 秒对 satellite 进行轮询断连重连，这是正常行为，不影响整体功能，但在边界条件下可能导致事件丢失。无需干预，记录备查。

---

## 12. 媒体播放器联动

### 语音控制本地 Squeezelite 播放器

利用 HA 的**区域感知（Area Awareness）**机制，无需编写代码实现语音媒体控制。

**配置步骤：**

1. **暴露播放器实体**
   进入 HA **设置 → 语音助手 → 暴露**，确保 `media_player.rpi_squeeze`（或对应实体名）对 Assist 可见。

2. **分配到同一区域**
   进入 HA **设置 → 区域与区域**，创建区域（如"桌面"），将 **Wyoming 卫星设备**和 **Squeezelite 播放器实体**分配到**同一区域**。

**效果：** 对着树莓派说"暂停"、"下一首"、"音量调到百分之五十"，HA 自动匹配该区域内的 `media_player` 并下发指令，不影响 PipeWire 混音比例。

### 唤醒时的播放器控制流（Python 层）

```
wyoming-satellite 检测到唤醒词
    ↓
UDP 信号发至 10701
    ↓
assistant_listener.py 接收
    ↓
main.py → 向 Squeezelite/LMS 发送 pause 命令
         + 弹出语音蒙版

语音交互完成，收到 done 信号（TTS音频必定已播放完毕）
    ↓
main.py → 发送 play 命令恢复播放
         + 立即关闭语音蒙版
```
