# 智能语音助手架构设计、诊断与演进全记录 (Voice Assistant Architecture)

本文档是由初版架构设计 (`Home_Assistant.md`) 与历次闭环诊断报告 (`voice_assistant_diagnosis.md`) 完整融合而成的全景技术长文。记录了在 `Ansible_RPI_Touch` 项目中引入语音助手时的选型历程、遇到的深水区技术瓶颈、详尽的根因分析、四次架构重构迭代（v1至v4），以及最终版的配置指南。

---

## 一、 背景与挑战

我们的目标是在现有的树莓派带屏音乐播放器（CPU 占用约 10%，UI 帧率 18 FPS）上，无缝融合一个智能语音助手。在这个过程中，我们遇到了三大“硬件与物理层面”的死结：

### 困境 1：回声消除（AEC）带来的空载损耗
如果要在播放音乐的同时能够“随时打断”并唤醒助手，必须开启 AEC 算法（过滤掉喇叭发出的音乐声，只保留人声）。
* **痛点**：软件 AEC 会导致树莓派在**待机和听歌时**的 CPU 占用率激增 20% 甚至更高，引起发热和功耗问题，严重破坏了原有系统精简高效的初衷。

### 困境 2：后端 HA 算力拉垮（Intel J3455 的诅咒）
常规的 Home Assistant 玩法是把录音发给 HA 虚拟机处理 STT（语音转文字）。
* **痛点**：用户的 HA 运行在 QNAP 453Bmini 虚拟机中，CPU 是古老的 Celeron J3455。该 CPU **硬件阉割了 AVX/AVX2 向量指令集**，导致在进行 AI 矩阵运算时极速拉垮。实测处理一句极短的指令，Whisper 需要卡顿 5 到 10 秒，体验犹如灾难。

### 困境 3：前端 RPi 算力抢占（UI 与音频卡顿）
既然 J3455 不行，那把 AI 丢给树莓派本地算呢？树莓派 4B (Cortex-A72) 自带 ARM NEON 向量加速，跑量化后的模型反而更快。
* **痛点**：在树莓派满负荷运算模型的那两秒钟里，CPU 占用高达 100%。如果此时后台还在播放高码率音乐，UI 的 SPI 通信和音频解码线程会瞬间被饿死，导致屏幕冻结和喇叭爆音。

---

## 二、 破局第一版：100% 边缘计算 (Edge AI)

面对上述死结，我们得出了一个极其巧妙且反直觉的破局思路：
> **“只要唤醒词一触发，就立刻暂停音乐。此时树莓派的 CPU 就彻底解放了，就算瞬间满载也不会有任何卡顿！”**

基于这个思路，我们彻底抛弃了云端和 AEC，确立了 **100% 本地化纯离线** 的极限压榨架构：

1. **日常待机（极低功耗）**
   * **放弃 AEC**：音乐播放声音太大时听不见唤醒词？那就不用它。大多数时候是不放歌的。
   * **轻量级唤醒**：在树莓派后台静默运行由 C 语言编写的 `Porcupine` 引擎，只听 "Bumblebee" 一个词，CPU 占用长期维持在 **1% ~ 2%**。
2. **唤醒拦截（瞬间释放算力）**
   * 一旦听到 "Bumblebee"，底层 `wyoming-satellite` 触发 UDP 钩子，向 Python UI 发送 `awake` 信号。
   * UI 进程瞬间截获指令，**向播放器发送 `pause` 命令**，同时弹出一个深色带动画的“语音悬浮蒙版”。
3. **算力燃烧（本地 AI 推理）**
   * 此时音乐已停，树莓派的 4 颗核心被完全释放，狂飙本地 STT 与 TTS 推理。由于播放器处于暂停状态，没有任何音频线程会被饿死。
4. **从容收尾**
   * 语音播报完毕，发送 `done` 信号，悬浮蒙版消失，程序自动发送 `play` 命令，音乐无缝恢复。

这套架构实现了四个完美的指标：**0 隐私泄露（全断网）、0 日常额外功耗增加、不需要独立显卡/高性能服务器、不牺牲 UI 体验。**

### 模块划分与数据流向
* **后台守护进程**：`wyoming-porcupine1` (10400 唤醒)，STT服务 (10300)，TTS服务 (10200)，`wyoming-satellite` (10700 大管家)。
* **Python 前端 UI 层**：`assistant_listener.py` (UDP 监听)，`ui_screen_assistant.py` (动画渲染)，`main.py` (逻辑融合)。

---

## 三、 第一代架构 (Whisper+Piper) 遇到的深水区瓶颈与根因诊断

在第一代架构运行过程中，我们遭遇了严重的性能和稳定性危机：**这不是死锁，不是状态机问题，也不是 ARM CPU 推理天生慢。**

### 🔬 实验验证与时间线对比
我们在 RPi 上进行了对比实验（通过 Wyoming 协议直连 Whisper 服务）：

| 实验 | 输入 | Whisper 推理耗时 | 结果 | 分析 |
|------|------|-----------------|------|------|
| 基准 | 3秒静音 | **3.25秒** ✅ | 空 | 直接调用模型 |
| Wyoming 服务 | 3秒纯噪音 | **2分20秒** 🔴 | 空（hallucination 后截断） | 服务端异常 |
| 实际 Session 3 | 4.08秒真实语音 | **6秒** ✅ | "打开客厅的灯。" | 语音清楚 |
| 实际 Session 4 | 4.37秒低信噪比 | **2分19秒** 🔴 | "打开小米台灯。" | 遭遇幻觉死循环 |

> [!IMPORTANT]
> 同样的模型、同样的硬件，**有真实语音的音频 6 秒搞定，纯噪音的 3 秒音频要 2 分 20 秒**。

### 根因分析
#### 问题 1：Whisper Hallucination 循环 🔴（主要瓶颈）
Whisper 的转录分两个阶段：
1. **Encoder**：提取特征 → ARM 上 1~2 秒 ✅。
2. **Decoder**：自回归生成 token → **在静音/噪音上失控**。

当音频中没有有效语音时，decoder 找不到结束点，会反复生成 `initial_prompt` 中的内容（"打开小米台灯、关上小米台灯..."），在 ARM 上每步 50~100ms，循环几百步累计分钟级别。这就是识别结果中莫名出现“打开小米台灯”的根因（被 decoder 反刍出来的 hallucination）。

#### 问题 2：HA Pipeline 的录音时长不可控 ⚠️
Session 1 录了 15 秒（HA pipeline 全局超时上限）。由于 HA 端的 VAD 没有生效或灵敏度不够，大量静音被发给了 Whisper，导致灾难级的处理延迟。

#### 问题 3：Piper TTS 完全不工作 🔴
日志显示 `ModuleNotFoundError: No module named 'unicode_rbnf'`。RPi 上的 Piper 缺少此依赖，导致中文 phonemize 失败，输出全是 0x00 的空 WAV 数据，最终引发 HA 端 ffmpeg 转码报错。

#### 问题 4：Satellite 轮询断连 ⚠️
HA 每 8 秒对 satellite 进行轮询断连重连，虽不影响整体功能，但易导致边界条件下的事件丢失。

### 阶段性紧急修复
1. 修复 Piper：`pip install unicode-rbnf`。
2. 给 Whisper 启用 Silero VAD 过滤：在服务中加上 `--vad-filter`，纯噪音在 1 秒内被跳过。
3. 调整 HA 端 "Finished speaking detection" 为 "Aggressive"。

---

## 四、 架构演进第二阶段 (v3)：时序、混音与增益调优全记录

### 1. 唤醒体验优化：增加音频反馈与防截断机制
* **问题**：唤醒后仅有界面变化，用户不知道何时可以说话。
* **修复**：在 `wyoming-satellite` 增加 `--awake-wav awake_prompt.wav` 参数实现“听觉+视觉”同步反馈；并将 UI 状态的硬编码超时由 **6 秒延长至 10 秒**，给予充足指令下达窗口。

### 2. 语音流切断机制（VAD）调优：修复“说话被强行打断”
* **问题**：用户语速较慢或停顿思考 2 秒，HA 就强行切断连接。
* **修复**：将 HA 中 Assistant 的 **Finished speaking detection** 从 Aggressive 改为 **Relaxed（宽松）**。

### 3. 音频输出架构升级：全面接入 PipeWire 混音
* **问题**：原输出命令 `aplay -D plughw:0` 独占声卡，与系统播放器冲突，且用 `sox` 强行放大 3 倍极易破音。
* **修复**：移除 ALSA 直连与 `sox`，改用 PulseAudio 兼容层 `--snd-command "paplay --raw --rate=22050 --channels=1 --format=s16le"`，实现语音提示与音乐的完美叠播混合，解决破音。

### 4. 麦克风增益悖论：修复“吼叫唤醒”与“30秒卡顿死锁”
* **问题**：必须大喊才能唤醒；但远处的电视杂音却被清晰收录，导致语音管家卡死 30 秒。
* **根因（AGC错位）**：本地 `sox -v 0.5` 让唤醒变弱，HA 云端收到微弱音频触发 Auto gain 暴力放大远场杂音，导致 VAD 无法截断。
* **修复**：删掉本地 `sox -v 0.5` 恢复原始拾音解决“吼叫”；在 HA 中 **关闭 Auto gain** 并将 **Noise suppression level 提至 High/Maximum** 解决卡死。

### 5. UI 气泡滚动渲染 Bug
* **问题**：多次对话后，HA 回复的气泡在屏幕上“消失”。
* **修复**：修改 `ui_screen_assistant.py` 坐标算法为 `cy = min(CHAT_TOP, CHAT_BOT - total_h)`，确保历史记录始终自底向上对齐。

### 6. UI 状态视觉与物理播放脱节：修复“锁死错觉”
* **问题**：对话气泡很快消失，但喇叭还在响，此时喊唤醒没反应（锁定中），用户误以为有 Bug。
* **修复**：将 `done` 状态的 `close_at` 延时从 4.0 秒延长至 **12.0 秒**，让气泡陪喇叭显示完。

### 7. 幽灵超时（25秒死锁）
* **问题**：唤醒后没说话，屏幕卡住傻等 25 秒后报错。
* **修复**：将 `awake` 兜底超时从 25.0 秒缩短至 **8.0 秒**，若 HA 默默挂断，屏幕也能迅速复位。

---

## 五、 极致优化阶段（v4）：引擎全量替换、100% 离线闭环与网络抗休眠加固

### 1. 核心引擎的彻底换血：引入 Sherpa-ONNX
* **背景**：Whisper 推理慢且易产生幻觉死锁，Piper 在本地依赖臃肿。
* **重构**：全面使用 `k2-fsa` 的 `sherpa-onnx` 框架替换原有组件。
  * **STT (SenseVoice-int8)**：全量驻留内存，完全无磁盘 I/O，极低延迟。底层算法从根本上避免了自回归幻觉。
  * **TTS (Matcha-Icefall zh-baker + Vocos)**：采用极速的流匹配非自回归合成算法与 vocos 声码器，纯 C++ 无依赖，发音自然饱满。

### 2. 经典“路由悖论”修复：树莓派的单向失联
* **现象**：树莓派本地音乐正常播放，但局域网电脑 Ping 不通且 SSH 断连（`No route to host`）。
* **根因**：树莓派闲置时 Wi-Fi 芯片进入 Power Save，无视入站 ARP 广播，但出站播放器 TCP 通信能反向唤醒它。
* **修复**：修改 NetworkManager 配置写入 `wifi.powersave = 2`，永久关闭网络休眠功能。

### 3. 真正的 100% 离线语音：原生 HA Intent 处理
* **问题**：原生 HA 听不懂“现在几点了”。早期在树莓派本地用 Python 拦截黑代码。
* **修复**：删除本地拦截逻辑，在 HA `configuration.yaml` 编写自定义 `intent_script`，并配合 `custom_sentences` 实现正统的 100% 离线播报。

#### 💡 实战范例：让离线 HA 听懂“几点了”和模糊灯控

**1. 意图响应配置 (HA `configuration.yaml`)**
在你的 Home Assistant 根配置中，利用 Jinja2 模板引擎抓取本地系统时间：
```yaml
intent_script:
  # 自定义获取时间的意图
  GetTimeIntent:
    speech:
      text: "现在是 {{ now().strftime('%p %I点%M分') | replace('AM', '上午') | replace('PM', '下午') }}"
```

**2. 句式捕获配置 (`custom_sentences/zh/custom.yaml`)**
在 HA 的 config 目录下创建 `custom_sentences/zh/custom.yaml` 文件（如果没有则新建目录）。在这里定义唤醒刚才那个意图的中文句子，并使用语法消除分词歧义：
```yaml
language: "zh"
intents:
  GetTimeIntent:
    data:
      - sentences:
          - "现在几点[了]"
          - "几点了"
          - "[告诉][我]时间"

  # 解决“关上客厅灯”被错误分词为“上客厅”的问题
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
这样不仅能让系统直接报时，还通过 `[上|闭]` 这样的可选语法和 `{name}` 槽位，彻底根治了中文词义切分错误导致的设备控制失败，而且**全程不需要连接任何外部大模型**。

---

## 六、 附录：架构演进过程中的核心选型反思与探讨纪要

在系统演进中，我们经历了以下关键的技术反思，这些成为了 V4 架构的基石：

1. **硬件算力分布的终极权衡**：为什么不交给 J3455 虚拟机？J3455 虽然是 x86 但阉割了 AVX 向量指令，矩阵运算极慢。RPi 4B 有完整 ARM NEON，必须将 STT 留在边缘端。
2. **打破“官方生态”盲目崇拜**：初期盲从 HA 官方强推的 Year of the Voice 标配 (Whisper+Piper)，但其在边缘计算和中文环境水土不服，造成严重性能拖累。这是一次为生态统一而牺牲性能的失误。
3. **NLU（语义理解）破局**：中文分词经常把“关上客厅灯”错分为“上客厅”。最终放弃本地拦截，改用 HA 的 `custom_sentences/zh.yaml` 通过正则表达式精准映射意图。
4. **终极解药 Sherpa-ONNX**：确定 Whisper (自回归) 框架对静音死循环是架构级硬伤，改用 Transducer/CTC 架构模型，彻底消灭幻觉，且纯 C++ 内核终结了 Python 依赖地狱。

---

## 七、 Home Assistant 最终配置指南

树莓派端由 Ansible 部署完毕后，它如同具备器官的身体，需在 HA 中帮它“接通神经”。

> [!WARNING]
> **千万不要使用 HA 的自动识别弹窗！**
> 新版 HA 会自动发现网络里的 `wyoming-satellite` 并弹出 **Voice Satellite setup**。**请直接无视/关闭此向导！** 如果误选“Full local processing”，HA 将在 J3455 虚拟机里部署笨重的插件导致卡顿瘫痪。

### 1. 手动接入 Wyoming 服务 (三大器官)
进入 HA 的 **配置 -> 设备与服务 -> 添加集成**，搜索 **Wyoming Protocol**，连续添加：
1. **添加大脑 (STT)**：填树莓派 IP，端口填对应的 Sherpa-ONNX STT 端口。
2. **添加嘴巴 (TTS)**：填树莓派 IP，端口填对应的 Sherpa-ONNX TTS 端口。
3. **添加身体 (Satellite)**：填树莓派 IP，端口填 `10700`。*(注：添加后 HA 会弹出 Voice Satellite setup 向导，请直接点击右上角 X 关闭)*

### 2. 防卡顿与截断的参数调整（关键！）
在 HA 的对应设备设置界面，请务必修改以下音频处理参数：
* **Finished speaking detection (语音结束检测)**：设为 **Relaxed (宽松)**，防止说话中途停顿被切断。
* **Auto gain (自动增益)**：**调低/关闭**，防止云端暴力放大电视背景音导致麦克风死锁。
* **Noise suppression level (降噪等级)**：设为 **High / Maximum**。

### 3. 组装“灵魂”助手 (Voice Assistant)
进入 HA 的 **配置 -> 语音助手 (Voice Assistants)**，点击 **+ 添加助手**：
* **名称**：Raspberry Pi Local Edge
* **语言**：中文 (Chinese)
* **对话代理 (Conversation agent)**：Home Assistant
* **语音转文字 (STT)**：选择刚才添加的 Sherpa-ONNX
* **文字转语音 (TTS)**：选择刚才添加的 Sherpa-ONNX
* **唤醒词**：（空着即可，本地 Porcupine 已代劳）

创建完成后，点击该助手右上角的三个点，选择 **设为默认 (Set as preferred)**。"Raspberry Pi Local Edge" 名字旁会出现五角星。

至此，全本地离线版、高性能、抗干扰的智能语音终端彻底竣工！
