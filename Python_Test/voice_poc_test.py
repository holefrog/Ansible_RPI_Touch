#!/usr/bin/env python3
import time
import queue
import wave
import subprocess
import numpy as np
import sounddevice as sd
import pvporcupine
from faster_whisper import WhisperModel

# ------------------------------------------------------------------------
# 这个脚本是一个极简的“纯本地语音 AI 闭环”概念验证 (PoC)。
# 流程：监听 "Bumblebee" -> 播报“Bumblebee听到” -> 录音 3 秒 -> Whisper 识别 -> 播报结果
# 注意：务必使用 pip install pvporcupine==1.9.5 以免遇到新版的 API Key 限制！
# ------------------------------------------------------------------------

# Porcupine v1.9 要求的固定块大小和采样率
RATE = 16000
CHUNK = 512

print("\n[初始化] 正在加载唤醒词模型 (Porcupine v1.9: bumblebee) ...")
porcupine = pvporcupine.create(keywords=["bumblebee"])

print("[初始化] 正在加载 STT 模型 (faster-whisper tiny-int8) ...")
stt = WhisperModel("tiny", device="cpu", compute_type="int8")

print("\n=======================================================")
print("✅ 系统就绪！请对麦克风说：'Bumblebee'")
print("=======================================================\n")

audio_queue = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)
    audio_queue.put(bytes(indata))

def synthesize_and_play(text):
    print(f"[TTS 播报] 准备朗读: {text}")
    subprocess.run(["espeak", "-v", "zh", text], stderr=subprocess.DEVNULL)

try:
    with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, dtype='int16', channels=1, callback=audio_callback):
        while True:
            pcm = audio_queue.get()
            
            # 1. 唤醒词检测
            pcm_array = np.frombuffer(pcm, dtype=np.int16)
            keyword_index = porcupine.process(pcm_array)
            
            if keyword_index >= 0:
                print("\n🔔 [触发] 检测到唤醒词 'Bumblebee'！")
                
                # 2. 先发声回应
                synthesize_and_play("Bumblebee听到，请继续")
                
                print("🎤 [录音] 开始录音 3 秒钟（请随便说句中文指令）...")
                
                # 录音前清空队列：把 TTS 播报期间麦克风录到的它自己的声音丢弃，防回音
                while not audio_queue.empty():
                    audio_queue.get()
                    
                # 3. 录音 3 秒
                frames = []
                for _ in range(int(RATE / CHUNK * 3)):
                    frames.append(audio_queue.get())
                    
                audio_data = b''.join(frames)
                
                # 保存临时录音
                with wave.open("/tmp/temp_cmd.wav", "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(RATE)
                    wf.writeframes(audio_data)
                    
                print("🧠 [STT] 录音结束，正在本地进行 Whisper 推理...")
                start_time = time.time()
                
                # 4. 语音转文字
                segments, info = stt.transcribe("/tmp/temp_cmd.wav", beam_size=1, language="zh")
                text = "".join([segment.text for segment in segments])
                
                process_time = time.time() - start_time
                print(f"📝 [STT 结果] '{text}' (耗时: {process_time:.2f} 秒)")
                
                # 5. 反馈执行结果
                if text.strip():
                    synthesize_and_play(f"收到指令。{text}")
                else:
                    synthesize_and_play("抱歉，我没有听清。")
                    
                print("\n=======================================================")
                print("✅ 循环结束，继续监听 'Bumblebee' ...")
                
                while not audio_queue.empty():
                    audio_queue.get()
                    
except KeyboardInterrupt:
    print("\n[退出] 测试结束。")
finally:
    if 'porcupine' in locals():
        porcupine.delete()
