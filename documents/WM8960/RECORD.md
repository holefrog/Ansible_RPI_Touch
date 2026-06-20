# WM8960 Audio Board 录音噪音问题排查与终极解决记录

## 1. 背景与问题现象
在树莓派 4B (Debian 13 Trixie) 上部署 Ansible 环境时，使用了 **WM8960 Audio Board** (SKU 15019) 进行音频测试。
- **问题现象**：播放音频（`aplay`）似乎正常，但录音（`arecord`）结果全是极低振幅的纯噪音，毫无有效声音信号（`sox stat` 显示最大振幅极低）。
- **官方技术支持反馈**：Waveshare 官方技术员在他们的树莓派上测试后表示“一切正常，能正常录音”。

## 2. 核心发现与排查历程 (我们是如何破案的)

经过两天的深入排查、阅读底层 C 语言驱动代码、对比原理图与设备树配置，我们找出了三个深层原因，这也解释了为什么官方技术员无法复现问题：

### 坑一：官方驱动与硬件版本的“张冠李戴”（最致命问题）
- **官方的测试环境**：技术员测试用的是 `WM8960-Audio-HAT`（专为树莓派设计的扩展板）。这款 HAT 板载的是 **12.288MHz** 晶振。
- **我们的真实硬件**：我们使用的是 `WM8960 Audio Board`（原本定位给 STM32 等单片机用的模块），其电路图（`WM8960_Audio_Board_Schematic..pdf`）明确标注使用的是 **24MHz** 晶振。
- **Linux 原生驱动的“毒药”**：树莓派 Linux 系统自带的 `dtoverlay=wm8960-soundcard` 设备树，实际上是 Waveshare 官方当年为 `HAT` 提交的，里面**硬编码写死了 `clock-frequency = <12288000>;`**。
- **灾难性后果**：内核按照 12.288MHz 来配置芯片的锁相环 (PLL) 和分频器，但物理时钟却是 24MHz。这导致 ADC（录音）的内部采样频率直接翻倍飙升到 90kHz 以上，而树莓派 I2S 接口依然按 48kHz 读取数据，导致数据帧完全错位、溢出和撕裂，录下来的必然是纯粹的数字垃圾。
- **为什么播放似乎正常？** 播放时，树莓派强制提供 I2S 时钟 (LRCLK)，WM8960 的 DAC 处于从机模式被迫同步，虽然内部 DSP 滤波器频率全乱了，但强制同步让它勉强发出了声音，掩盖了这个致命的时钟错误。

### 坑二：单双声道的物理差异
- `HAT` 硬件有左右两个独立麦克风。
- 我们的 `Audio Board` **只有一个单声道麦克风**，物理连接在左声道（`LINPUT1`），右声道物理悬空。如果直接录制立体声，右声道必然全是底噪。

### 坑三：找不到的 Mic Bias 开关与 DAPM 机制
- 我们一开始怀疑麦克风没有供电（Mic Bias 未开启），但在 `alsamixer` 里怎么都找不到开关。
- 研究 ALSA 底层驱动发现，WM8960 驱动启用了 **DAPM (动态音频电源管理)** 机制。Mic Bias 不是手动开启的，而是**当且仅当音频输入链路被完整打通时，系统才会自动为其供电**。我们需要通过 `amixer` 将 `LINPUT1` 一路通向 `ADC`，电源才会自动给上。

---

## 3. 终极解决方案 (Ansible 原生自动化部署)

为了彻底摆脱“有毒”的原生设备树，且不依赖官方提供的旧版 Shell 脚本安装包，我们设计了一套**纯粹基于 Ansible 的自动化原生部署方案**。

### 第一步：编写专属的 24MHz 设备树 (DTS)
我们在 Ansible 项目的 `roles/system/files/wm8960-audio-board.dts` 中，基于原生驱动修改出了一份专属的 Overlay，最关键的是修复了时钟频率：
```dts
// ... 摘录关键部分 ...
wm8960_mclk: wm8960_mclk {
    compatible = "fixed-clock";
    #clock-cells = <0>;
    clock-frequency = <24000000>; /* 修复为 24MHz 晶振 */
};
// ...
```

### 第二步：Ansible 自动化编译与内核加载
在 `hw_wm8960.yml` 部署剧本中，增加自动化任务：
1. 确保目标机器安装 `device-tree-compiler`。
2. 自动拷贝 `wm8960-audio-board.dts` 到目标机器。
3. 执行 `dtc` 命令将其编译为 `/boot/firmware/overlays/wm8960-audio-board.dtbo`。
4. 修改 `/boot/firmware/config.txt`，移除旧的 `wm8960-soundcard`，应用全新的 `dtoverlay=wm8960-audio-board`。

### 第三步：ALSA 链路打通与单声道映射
在系统启动并识别到专属声卡后，通过一连串 `amixer` 命令打通左声道链路以激活 DAPM，同时将左声道数据复制到右声道以实现完美的“单声道录立体声”：
```bash
# 为了防止设备号变动，统一使用声卡名称 -c wm8960audioboar
# 1. 开启左声道输入到 Boost Mixer 的开关 (触发 DAPM 自动开启 Mic Bias)
amixer -c wm8960audioboar cset name='Left Boost Mixer LINPUT1 Switch' on

# 2. 开启 Boost Mixer 到 Input Mixer 的开关
amixer -c wm8960audioboar cset name='Left Input Mixer Boost Switch' on

# 3. 开启 ADC 捕获的总开关
amixer -c wm8960audioboar cset name='Capture Switch' on

# 4. 设置捕获音量
amixer -c wm8960audioboar cset name='Capture Volume' 63
amixer -c wm8960audioboar cset name='ADC PCM Capture Volume' 255

# 5. 【最关键的映射】将左侧单声道 ADC 数据复制给双声道的左右音轨
amixer -c wm8960audioboar cset name='ADC Data Output Select' 1
```

---

## 4. 验证结果与正确录音姿势
应用上述修复部署后重启，使用以下命令进行录音测试：

### ❌ 错误的录音姿势 (产生白噪声)
```bash
arecord -Dplughw:0 -f cd -d 5 test.wav
```
**原因**：`-f cd` 代表请求 16-bit 44100Hz 的数据。原生的底层驱动此时暴露的硬件最原始支持位宽是 24-bit/32-bit (S24_LE/S32_LE)。如果使用 ALSA 的软件转换层 `plughw:0` 试图向下截断 (32转16) 或者降频 (48000转44100)，在树莓派平台上极易触发字节序或对齐 BUG，导致音频完全破音，输出刺耳的白噪音。

### ✅ 正确的终极测试命令 (获取完美数据)
必须绕过所有的中间件，直通硬件 (`hw:0`)，并完全匹配硬件支持的最高采样格式（32-bit, 48000Hz）：
```bash
arecord -Dhw:0 -f S32_LE -r 48000 -c 2 -d 5 test.wav
sox test.wav -n stat
```

**测试数据表明**：
- `Samples read` 精准为 `480000` (48000Hz * 5秒 * 2通道，毫无丢帧)。
- `Maximum amplitude` 达到了完美的满幅 `1.000000`。
- `RMS amplitude` 达到 `0.367895`。
- 播放 `test.wav`，声音极其清晰饱满，纯噪音彻底消失。至此，WM8960 Audio Board 在树莓派上的驱动冲突问题被彻底、完美地解决。
