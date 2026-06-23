#!/usr/bin/env python
# resources/ts/state_manager.py
# v2

import time
import threading
import logging

from query_source import get_high_priority_source
from query_system import get_system_info, get_services_status
from state_handlers import (
    handle_airplay_state,
    handle_bluetooth_state,
    handle_lms_or_idle_state
)

logger = logging.getLogger("StateManager")


class VoiceSession:
    """语音会话状态容器"""
    def __init__(self):
        self.history = []          # [{"user": str, "assistant": str, "state": str}]
        self.voice_state = "idle"  # idle / listening / processing / speaking
        self.transcript_text = ""
        self.close_at = 0.0        # 非零时表示定时关闭，由 UIManager 消费
        
        # 跨域状态记录：由 StateManager 内部全权维护
        self.is_active = False
        self.was_playing_before_voice = False


class StateManager:
    """
    全局状态大管家：封装所有后台轮询线程和互斥锁。
    对外提供极其干净的接口，隔绝主程序的线程复杂性。
    """
    def __init__(self, pactl_env, lms_params, touch_dev):
        self.pactl_env = pactl_env
        self.lms_params = lms_params
        self.touch_dev = touch_dev

        # --- 触摸状态 ---
        self._touch_events = []  # 升级为事件队列，避免高速滑屏时丢失动作
        self._touch_lock = threading.Lock()

        # --- 音频与系统状态 ---
        self._player_state = None
        self._system_info = {}
        self._services_status = {}
        self._app_state_lock = threading.Lock()

        # --- 语音会话状态 ---
        self._voice_session = VoiceSession()

    def start_background_threads(self):
        """一键启动所有后台数据采集线程"""
        threading.Thread(target=self._touch_poller, daemon=True).start()
        threading.Thread(target=self._audio_polling_thread, daemon=True).start()
        threading.Thread(target=self._info_polling_thread, daemon=True).start()

    def advance_voice_state(self, event: dict) -> VoiceSession:
        """
        根据来自 AssistantListener 的事件推进语音会话状态。
        由 main.py 主循环调用，返回最新的 VoiceSession 引用。
        """
        evt_type = event.get("event")
        with self._app_state_lock:
            s = self._voice_session

            if evt_type == "awake":
                if not s.is_active:
                    s.is_active = True
                    # 自动读取内部的 _player_state 记录现场
                    is_playing = (self._player_state is not None
                                  and not getattr(self._player_state, "is_paused", True)
                                  and not getattr(self._player_state, "is_clock", False))
                    s.was_playing_before_voice = is_playing
                    s.voice_state = "listening"
                    s.transcript_text = ""
                    s.close_at = time.time() + 10.0  # 兜底超时时间（增加以包容1秒的提示音及用户的语音输入）
                    s.history.append({"user": "", "assistant": "", "state": "listening"})
            elif evt_type == "synthesize":
                if s.history:
                    text = event.get("text", "").strip()
                    if text.startswith('"') and text.endswith('"'):
                        text = text[1:-1]
                    s.history[-1]["assistant"] = text.replace('\\n', ' ').strip()
                    s.voice_state = "speaking"

            elif evt_type == "transcript":
                s.voice_state = "processing"
                s.transcript_text = event.get("text", "")
                s.close_at = time.time() + 20.0  # 重置兜底超时
                if s.history:
                    s.history[-1]["user"] = s.transcript_text
                    s.history[-1]["state"] = "processing"

            elif evt_type == "tts-start":
                s.voice_state = "speaking"
                s.close_at = time.time() + 60.0  # 播报语音可能会很久，给足时间
                if s.history:
                    s.history[-1]["state"] = "speaking"

            elif evt_type in ("done", "timeout", "error"):
                s.voice_state = "idle"
                s.is_active = False  # 状态机完全复位
                if s.history:
                    s.history[-1]["state"] = evt_type
                s.close_at = time.time() + 12.0

            return s

    def get_voice_session(self) -> VoiceSession:
        """安全获取当前语音会话状态"""
        with self._app_state_lock:
            return self._voice_session

    def get_touch_event(self):
        """安全的消费接口：获取并清空最新触摸事件"""
        with self._touch_lock:
            if self._touch_events:
                return self._touch_events.pop(0)
            return None

    def get_app_state(self):
        """安全的消费接口：获取最新应用和系统状态拷贝"""
        with self._app_state_lock:
            return self._player_state, dict(self._system_info), dict(self._services_status)

    # ================= 内部后台轮询线程 =================
    def _touch_poller(self):
        is_touching = False
        empty_count = 0
        last_x = last_y = 0
        while True:
            try:
                points, coords = self.touch_dev.get_touch_xy()
                if points > 0:
                    empty_count = 0
                    mapped_x = 479 - coords[0]['y']
                    mapped_y = 319 - coords[0]['x']
                    with self._touch_lock:
                        if not is_touching:
                            is_touching = True
                            self._touch_events.append(("DOWN", mapped_x, mapped_y))
                        else:
                            # 如果是连续 MOVE，替换队尾的 MOVE 事件以防队列堆积爆炸
                            if self._touch_events and self._touch_events[-1][0] == "MOVE":
                                self._touch_events[-1] = ("MOVE", mapped_x, mapped_y)
                            else:
                                self._touch_events.append(("MOVE", mapped_x, mapped_y))
                    last_x, last_y = mapped_x, mapped_y
                else:
                    empty_count += 1
                    if empty_count >= 2:
                        if is_touching:
                            with self._touch_lock:
                                self._touch_events.append(("UP", last_x, last_y))
                        is_touching = False
            except Exception:
                pass
            time.sleep(0.02)

    def _audio_polling_thread(self):
        current_active_type = None
        last_known_volume = -1
        while True:
            try:
                source_type, source_status = get_high_priority_source(self.pactl_env)
                new_state = None

                if source_type == "airplay":
                    new_state = handle_airplay_state(self.pactl_env, source_status, last_known_volume, self.lms_params)
                elif source_type == "bluetooth":
                    new_state = handle_bluetooth_state(self.pactl_env, source_status, last_known_volume)
                else:
                    new_state = handle_lms_or_idle_state(self.pactl_env, self.lms_params, current_active_type, last_known_volume)

                if new_state:
                    current_active_type = new_state.active_player_type
                    if new_state.volume >= 0:
                        last_known_volume = new_state.volume
                    with self._app_state_lock:
                        self._player_state = new_state
            except Exception as e:
                logger.error(f"Audio polling thread error: {e}")
            time.sleep(1.0)

    def _info_polling_thread(self):
        while True:
            try:
                sys_info = get_system_info()
                svc_status = get_services_status()
                with self._app_state_lock:
                    self._system_info = sys_info
                    self._services_status = svc_status
            except Exception as e:
                logger.error(f"Info polling thread error: {e}")
            time.sleep(5)