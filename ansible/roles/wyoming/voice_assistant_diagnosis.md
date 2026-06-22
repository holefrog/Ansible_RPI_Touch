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
