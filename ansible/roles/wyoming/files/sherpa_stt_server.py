# sherpa_stt_server.py v1
# Wyoming STT server using sherpa-onnx SenseVoice
# Replaces wyoming-faster-whisper on port 10300

import argparse
import asyncio
import logging
import numpy as np
import sherpa_onnx
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.asr import Transcribe, Transcript
from wyoming.event import read_event, write_event
from wyoming.info import AsrModel, AsrProgram, Attribution, Describe, Info

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--model-dir", required=True, help="Path to model directory")
parser.add_argument("--port", type=int, default=10300, help="Port to listen on")
args = parser.parse_args()

MODEL_DIR = args.model_dir
PORT = args.port

# 进程级共享，线程安全
recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=f"{MODEL_DIR}/model.int8.onnx",
    tokens=f"{MODEL_DIR}/tokens.txt",
    use_itn=True,          # 数字/标点还原
    language="zh",
    debug=False,
)

INFO = Info(
    asr=[
        AsrProgram(
            name="sherpa-stt",
            description="SenseVoice offline STT",
            attribution=Attribution(name="k2-fsa", url="https://github.com/k2-fsa/sherpa-onnx"),
            installed=True,
            models=[
                AsrModel(
                    name="sense-voice-zh",
                    description="SenseVoice Chinese int8",
                    attribution=Attribution(name="k2-fsa", url="https://github.com/k2-fsa/sherpa-onnx"),
                    installed=True,
                    languages=["zh"],
                )
            ],
        )
    ]
)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    logger.info("Connected: %s", addr)
    audio_buffer = []

    try:
        while True:
            event = await read_event(reader)
            if event is None:
                break

            if Describe.is_type(event.type):
                await write_event(INFO.event(), writer)

            elif AudioStart.is_type(event.type):
                audio_buffer = []

            elif AudioChunk.is_type(event.type):
                chunk = AudioChunk.from_event(event)
                # satellite 已经是 16kHz/16-bit/mono，直接转 float32
                samples = np.frombuffer(chunk.audio, dtype=np.int16).astype(np.float32) / 32768.0
                audio_buffer.append(samples)

            elif AudioStop.is_type(event.type):
                if audio_buffer:
                    audio = np.concatenate(audio_buffer)
                    stream = recognizer.create_stream()
                    stream.accept_waveform(16000, audio)
                    
                    # 在线程池跑推理，不阻塞事件循环
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, recognizer.decode_stream, stream)
                    
                    text = stream.result.text.strip()
                    logger.info("Transcript: %r", text)
                else:
                    text = ""
                await write_event(Transcript(text=text).event(), writer)
                audio_buffer = []

    except Exception:
        logger.exception("Client error: %s", addr)
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info("Disconnected: %s", addr)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = await asyncio.start_server(handle_client, "0.0.0.0", PORT)
    logger.info("STT server listening on port %d", PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
