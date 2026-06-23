# sherpa_tts_server.py v1
# Wyoming TTS server using sherpa-onnx matcha-icefall-zh-baker
# Replaces wyoming-piper on port 10200

import argparse
import asyncio
import logging
import numpy as np
import sherpa_onnx
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.tts import Synthesize
from wyoming.event import async_read_event, async_write_event
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--model-dir", required=True, help="Path to model directory")
parser.add_argument("--port", type=int, default=10200, help="Port to listen on")
args = parser.parse_args()

MODEL_DIR = args.model_dir
PORT = args.port
SAMPLE_RATE = 22050
CHUNK_SIZE = 4096  # samples per AudioChunk

# 进程级共享
tts = sherpa_onnx.OfflineTts(
    sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                acoustic_model=f"{MODEL_DIR}/model-steps-3.onnx",
                vocoder=f"{MODEL_DIR}/hifigan_v2.onnx",
                lexicon=f"{MODEL_DIR}/lexicon.txt",
                tokens=f"{MODEL_DIR}/tokens.txt",
                dict_dir=f"{MODEL_DIR}/dict",
                data_dir=f"{MODEL_DIR}/espeak-ng-data",
            ),
            provider="cpu",
            num_threads=2,
            debug=False,
        ),
        rule_fsts=f"{MODEL_DIR}/phone.fst,{MODEL_DIR}/date.fst,{MODEL_DIR}/number.fst",
        max_num_sentences=1,
    )
)

INFO = Info(
    tts=[
        TtsProgram(
            name="sherpa-tts",
            description="Matcha Chinese TTS",
            attribution=Attribution(name="k2-fsa", url="https://github.com/k2-fsa/sherpa-onnx"),
            installed=True,
            version="1.0",
            voices=[
                TtsVoice(
                    name="zh-baker",
                    description="Chinese female voice",
                    attribution=Attribution(name="k2-fsa", url="https://github.com/k2-fsa/sherpa-onnx"),
                    installed=True,
                    version="1.0",
                    languages=["zh"],
                )
            ],
        )
    ]
)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    logger.info("Connected: %s", addr)

    try:
        while True:
            event = await async_read_event(reader)
            if event is None:
                break

            if Describe.is_type(event.type):
                await async_write_event(INFO.event(), writer)

            elif Synthesize.is_type(event.type):
                synthesize = Synthesize.from_event(event)
                text = synthesize.text
                logger.info("Synthesize: %r", text)

                # 在线程池跑推理，不阻塞事件循环
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None, lambda: tts.generate(text=text, sid=0, speed=1.0)
                )

                samples = np.array(result.samples, dtype=np.float32)
                pcm = (samples * 32767).clip(-32768, 32767).astype(np.int16).tobytes()

                await async_write_event(
                    AudioStart(rate=SAMPLE_RATE, width=2, channels=1).event(), writer
                )

                # 分块发送
                for i in range(0, len(pcm), CHUNK_SIZE * 2):
                    chunk = pcm[i : i + CHUNK_SIZE * 2]
                    await async_write_event(
                        AudioChunk(
                            rate=SAMPLE_RATE, width=2, channels=1, audio=chunk
                        ).event(),
                        writer,
                    )

                await async_write_event(AudioStop().event(), writer)

    except Exception:
        logger.exception("Client error: %s", addr)
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info("Disconnected: %s", addr)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = await asyncio.start_server(handle_client, "0.0.0.0", PORT)
    logger.info("TTS server listening on port %d", PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
