#!/usr/bin/env python3
import socket
import json
import threading
import queue
import logging

logger = logging.getLogger("AssistantListener")

class AssistantListener:
    """
    UDP 监听器（运行在主线程中的异步任务）
    用于接收来自 Linux Voice Assistant (LVA) 触发的各种状态事件（如唤醒、识别出文字、结束等），
    并将其放入 asyncio Queue 中供主循环消费。
    """
    def __init__(self, host='127.0.0.1', port=10701):
        self.host = host
        self.port = port
        self.event_queue = queue.Queue()
        self.running = False
        self.sock = None
        self.thread = None

    def start(self):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # 绑定端口，如果被占用可能会抛异常，这里我们做一层保护
        try:
            self.sock.bind((self.host, self.port))
            logger.info(f"🎤 语音助手监听器已启动 UDP {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"语音助手 UDP 端口绑定失败: {e}")
            self.running = False
            return

        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def _listen_loop(self):
        while self.running:
            try:
                # 阻塞接收，UDP 数据包一般很小，1024 足够
                data, addr = self.sock.recvfrom(1024)
                if not data:
                    continue
                    
                payload = data.decode('utf-8').strip()
                try:
                    event_obj = json.loads(payload)
                    self.event_queue.put(event_obj)
                    logger.debug(f"收到语音事件: {event_obj}")
                except json.JSONDecodeError:
                    logger.warning(f"收到非 JSON 数据: {payload}")
                    
            except socket.error as e:
                if self.running:
                    logger.error(f"UDP 接收错误: {e}")
                break
            except Exception as e:
                logger.error(f"AssistantListener 内部错误: {e}")

    def get_event(self):
        """
        安全的消费接口：获取最新事件。非阻塞。
        返回字典 e.g. {"event": "awake"}, {"event": "transcript", "text": "打开灯"}
        """
        try:
            return self.event_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
