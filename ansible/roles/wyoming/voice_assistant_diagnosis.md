# 语音助手闭环诊断报告 (v2)

## 结论

**不是死锁，不是状态机问题，也不是 ARM CPU 推理天生慢。** 根因是 **Whisper decoder 在静音/噪音上陷入 hallucination 循环**，加上 Piper TTS 缺少依赖导致语音合成全部失败。

---

## 🔬 实验验证

在 RPi 上进行了三组对比实验（通过 Wyoming 协议直连 Whisper 服务 10300 端口）：

| 实验 | 输入 | Whisper 推理耗时 | 结果 |
|------|------|-----------------|------|
| 基准（直接调用模型） | 3秒静音 | **3.25秒** ✅ | 空 |
| Wyoming 服务 | 3秒纯噪音 | **2分20秒** 🔴 | 空（hallucination 后截断） |
| 实际语音 session 3 | 4秒真实语音 | **6秒** ✅ | "打开客厅的灯。" |
| 实际语音 session 4 | 4秒（疑似低信噪比） | **2分19秒** 🔴 | "打开小米台灯。"（hallucination） |

> [!IMPORTANT]
> 同样的模型、同样的硬件，**有真实语音的音频 6 秒搞定，纯噪音的 3 秒音频要 2 分 20 秒**。
> 差异在于 decoder 的迭代次数：真实语音几步就收敛，噪音上 decoder 会持续产出 hallucinated tokens。

---

## 根因分析

### 问题 1：Whisper Hallucination 循环 🔴（主要瓶颈）

Whisper 的转录分两个阶段：
1. **Encoder**：对整段音频做特征提取 → ARM 上大约 1~2 秒 → ✅ 很快
2. **Decoder**：自回归生成 token → **在静音/噪音上失控**

当音频中没有有效语音时，decoder 会：
- 反复生成 `initial_prompt` 中的内容（"打开小米台灯、关上小米台灯..."）
- 每个 token 都要做完整的 cross-attention 计算
- 在 ARM Cortex-A72 上，每步需要约 50~100ms
- 循环几百步 → 累计分钟级别

**你说的"指令根本没提到小米台灯"完全正确** — 识别结果中的 "打开小米台灯" 不是你说的，而是 `initial_prompt` 被 decoder 反刍出来的 hallucination。

### 为什么有时快有时慢？

取决于 **录音中有效语音的信噪比**：

```
有效语音 → encoder 提取到特征 → decoder 几步收敛 → 3~6 秒 ✅
静音/噪音 → encoder 特征空洞 → decoder 找不到结束点 → hallucination 循环 → 2分钟 🔴
```

### 问题 2：HA Pipeline 的录音时长不可控 ⚠️

从日志看，Session 1 录了 **15.000 秒**（正好是 HA pipeline 的全局超时上限）。这意味着：
- HA 端的 VAD（语音结束检测）**没有生效或灵敏度不够**
- satellite 一直在流式发送音频给 HA
- HA 在 15 秒超时后才截断 → 大量静音被发给了 Whisper

当真实语音只有 2~3 秒，其余 12 秒全是静音/噪音时，情况就更糟。

### 问题 3：Piper TTS 完全不工作 🔴

从你提供的 HA 日志：

```
ModuleNotFoundError: No module named 'unicode_rbnf'    (RPi 端 Piper 崩溃)
     ↓
Piper 输出空 WAV 数据（全是 0x00）
     ↓
HA 端 ffmpeg 收到: "invalid start code [0][0][0][0] in RIFF header"
     ↓
HomeAssistantError: Unexpected error while running ffmpeg
```

**根因**：RPi 上的 Piper venv 缺少 `unicode_rbnf` 依赖 → 中文 phonemize 失败 → WAV 数据为空 → HA 端 ffmpeg 转码报错。

**修复**：
```bash
/home/player/wyoming/piper/bin/pip install unicode-rbnf
systemctl --user restart wyoming-piper
```

### 问题 4：Satellite 每 8 秒断连重连 ⚠️

```
Server disconnected → Server set → Waiting for wake word → Loading bumblebee
（每 ~8 秒循环一次）
```

这是 HA 的 Wyoming 集成对 satellite 做的轮询式连接管理。不影响功能，但如果断连恰好发生在语音处理的关键时刻，可能导致事件丢失。

---

## 完整事件时间线

### Session 4（20:40，最后一次语音交互）

| 时间 | 事件 | 耗时 | 备注 |
|------|------|------|------|
| `20:40:45` | Porcupine 检测到 "bumblebee" | — | ✅ |
| `20:40:45` | satellite 发 `awake` UDP → UI 显示语音界面 | < 1s | ✅ |
| `20:40:45` | satellite 开始流式录音给 HA | — | |
| `20:40:50` | Whisper 收到音频 (4.37秒) | 5s传输 | 这5秒包含了录音+VAD判定+网络传输 |
| `20:40:50` | **Whisper 开始推理** | — | **此处开始卡顿** |
| `20:43:09` | **Whisper 输出结果** | **⏱️ 2分19秒** | decoder hallucination |
| `20:43:09` | HA 返回 synthesize "小米台灯已打开" | < 1s | ✅ |
| `20:43:09` | HA 调用 Piper TTS | — | 💥 TTS 崩溃 |

### 各 Session 对比

| # | 唤醒 → 结果 | 音频长度 | 推理耗时 | 识别文本 | 分析 |
|---|-----------|---------|---------|---------|------|
| 1 | 20:04:17→20:06:36 | 15秒 | **2分02秒** | "机器是什么小米台的灯..." | 🔴 录到超时，全是hallucination |
| 2 | 20:06:39→20:07:34 | 2.69秒 | **52秒** | "打开小米台。打开小米台。" | 🔴 信噪比差，部分hallucination |
| 3 | 20:19:33→20:19:43 | 4.08秒 | **6秒** | "打开客厅的灯。" | ✅ 语音清楚 |
| 4 | 20:40:45→20:43:09 | 4.37秒 | **2分19秒** | "打开小米台灯。" | 🔴 hallucination |

---

## 修复方案

### 紧急修复（立即可做）

#### 1. 修复 Piper TTS

```bash
ssh player@192.168.50.207
/home/player/wyoming/piper/bin/pip install unicode-rbnf
systemctl --user restart wyoming-piper
```

#### 2. 给 Whisper 启用内置 VAD 过滤

在 [wyoming-whisper.service](file:///home/david/Coding/Ansible_RPI_Touch/ansible/roles/touchscreen/files/ui_config.toml) 中加上 `--vad-filter` 参数。这会让 Whisper 在推理前先用 Silero VAD 过滤掉静音段，**极大减少 hallucination**：

```ini
# wyoming-whisper.service 修改 ExecStart：
ExecStart=... --vad-filter
```

> [!IMPORTANT]
> 这是**最关键的一步**。启用 VAD 后：
> - 纯噪音/静音的音频会被直接跳过，返回空结果 → 从 2 分钟降到 < 1 秒
> - 有真实语音的音频只处理语音段 → 保持 3~6 秒的正常速度

### 优化项（推荐）

#### 3. 在 HA 端调整 "Finished speaking detection" 灵敏度

**HA → 配置 → 语音助手 → 你的助手 → Finished speaking detection** → 设为 **"Aggressive"**（0.25 秒静音即截断）

这样 HA 会更快地发 AudioStop 给 Whisper，减少发送无效音频。

#### 4. 考虑缩短或移除 `initial_prompt`

当前 initial_prompt 很长：
```
打开小米台灯。关上小米台灯。打开客厅的灯。关上客厅的灯。现在几点了？大点声，小点声，暂停，继续播放，下一首，上一首。
```

长 prompt 会：
- 增加 decoder 的上下文窗口 → 每步推理更慢
- 成为 hallucination 的"素材"，被反复生成

建议精简为最核心的几个短语，或完全移除（依靠 VAD 过滤来避免 hallucination）。

---

## 修复后的预期效果

| 指标 | 当前 | 修复后 |
|------|------|--------|
| 正常语音识别 | 6秒（偶尔正常） | **3秒** |
| 噪音/静音处理 | **2分钟+** | **< 1秒**（VAD跳过） |
| TTS 回复播放 | ❌ 完全不工作 | ✅ 正常播放 |
| Hallucination | 频繁（反刍 prompt） | 极少（VAD 过滤） |

---

## 全新第二阶段（v3）：全链路时序、混音与增益调优 (2026-06-23)

在此阶段，我们用 `sherpa-onnx` 彻底替换了 Whisper STT 和 Piper TTS，并解决了伴随而来的一系列体验问题。

### 1. 唤醒体验优化：增加音频反馈与防截断机制
- **问题**：唤醒后仅有界面变化，用户不知道何时可以开始说话。若加入唤醒提示音，又极易导致 UI 提早超时退出。
- **修复**：
  1. 在 `wyoming-satellite.service.j2` 中加入 `--awake-wav awake_prompt.wav` 参数，实现“听觉+视觉”同步反馈。
  2. 修改 `ansible/roles/touchscreen/files/state_manager.py`，将 UI 的硬编码超时时间由 **6 秒延长至 10 秒**，给予充足的指令下达窗口。

### 2. 语音流切断机制（VAD）调优：修复“说话中途被强行打断”
- **问题**：用户语速较慢或中途停顿思考了约 2 秒钟，HA 就会强行切断连接，指令被中途腰斩。
- **根因**：Home Assistant 语音管家（Assist Pipeline）中的 **VAD（Voice Activity Detection，静音检测）** 超时设定过短。
- **修复**：在 HA 网页端 Assistant 设置界面中，将 **Finished speaking detection** 设置修改为 **Relaxed（宽松）**。

### 3. 音频输出架构升级：全面接入 PipeWire 混音
- **问题**：原有输出命令 `aplay -D plughw:0` 会独占声卡，极易与系统中的 Squeezelite、Airplay 产生冲突。且强行使用 `sox` 放大 3 倍极易产生破音。
- **修复**：
  1. 从配置中彻底移除了 ALSA 直连和 `sox` 暴力放大。
  2. 改为使用 PulseAudio 兼容层的 `paplay`，精简为 `--snd-command "paplay --raw --rate=22050 --channels=1 --format=s16le"`。
- **收益**：语音助手的提示音和 TTS 回复能与背景音乐完美混合并叠播，且基于系统的底层路由使得声音响度直接恢复正常，杜绝了破音风险。

### 4. 麦克风增益悖论：修复“吼叫唤醒”与“30秒卡顿死锁”
- **问题**：在安静环境下必须对着麦克风大喊才能唤醒；但远处的电视杂音却被清晰收录，甚至导致语音管家卡死长达 30 秒。
- **根因（AGC错位）**：
  1. 麦克风本地强制使用了 `sox -v 0.5`，导致音量直接砍半。本地唤醒引擎（Porcupine）收音极其微弱，迫使用户大喊。
  2. HA 云端收到微弱音频后，触发了自带的 **Auto gain (自动增益)**，暴力放大了环境中的远场电视背景音。
  3. 背景噪音导致 HA 的 VAD 检测不到静音，录音一直持续直至触发 30 秒强制超时上限。
- **修复**：
  1. **本地修改**：删除了 `wyoming-satellite` 麦克风参数中的 `sox -v 0.5`，恢复 100% 原始拾音，解决了“吼叫唤醒”问题。
  2. **HA 设置**：在 HA 界面中**调低/关闭 Auto gain**，并将 **Noise suppression level** 提升至 **High/Maximum**，压制云端干扰，成功修复 30 秒卡顿死锁。

### 5. UI 气泡滚动渲染 Bug：修复“HA 回复文本不显示”
- **问题**：刚启动时头两句对话正常，多聊几句后，HA 的回复气泡在屏幕上“消失”，但物理喇叭能正常出声。
- **根因**：UI 的气泡坐标系算法错误。当聊天记录总高度超过屏幕高度时，代码使用 `cy = max(CHAT_TOP, CHAT_BOT - total_h)` 强制将历史消息顶端对齐，导致最新生成的气泡被挤出了屏幕下边缘。
- **修复**：修改 `ui_screen_assistant.py` 中的坐标系算法为 `cy = min(CHAT_TOP, CHAT_BOT - total_h)`，确保历史记录始终自底向上对齐，最新的气泡永远贴紧屏幕底部。

### 6. UI 状态视觉与物理播放脱节：修复“回复后退出，锁死 10 多秒”错觉
- **问题**：用户发现对话气泡很快消失（仿佛已退出），但此时喊唤醒词没反应，大约要等 10 多秒才能再次唤醒，误以为有倒计时 Bug。
- **根因**：
  1. HA 生成 TTS 极快，`wyoming-satellite` 下载完音频后会**立刻触发 `done.sh`**，导致 UI 气泡开始倒计时关闭。
  2. 但底层的喇叭（`paplay`）其实还在**花 5 到 8 秒钟慢条斯理地播放音频**。
  3. 为了防止“自己唤醒自己”（回声干扰），卫星进程在音频**物理播放完毕前，会强制锁定麦克风**。
  4. 视觉与听觉脱节：气泡由于硬编码了 4 秒自动消失，导致气泡没了喇叭还在响。用户以为结束了，其实麦克风还在锁定中。
- **修复**：修改 `state_manager.py`，将 `done` 状态的 `close_at` 延时从 4.0 秒延长至 **12.0 秒**。让气泡老老实实陪着喇叭显示完，消除“已退出却不理人”的错觉。

### 7. 幽灵超时（25秒死锁）：修复无有效语音时的“连接超时”
- **问题**：用户唤醒后若停顿时间稍微长了一点没说话，屏幕会卡在 Listening 状态傻等，足足等 25 秒后弹出“⚠ 连接超时”并退出。
- **根因**：
  1. 唤醒后，HA 的 VAD 发现超过 2 秒没听到有效语音，会判定用户不想说话，于是**直接单方面切断 TCP 连接**（静音截断）。
  2. HA 挂断时不会发送标准的 `Error` 或 `Done` UDP 事件给卫星进程。
  3. 由于没有收到结束信号，屏幕 UI 完全不知道连接已断，只能硬扛代码里设定的 25 秒“兜底超时时间”，然后抛出超时警告。
- **修复**：在 `state_manager.py` 中，将 `awake` 状态的兜底等待时间从 25.0 秒大幅缩短至 **8.0 秒**。若 HA 因没听清而默默挂断，屏幕也能迅速在 8 秒内复位，允许用户立刻重新唤醒。
