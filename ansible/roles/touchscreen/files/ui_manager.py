#!/usr/bin/env python
# resources/ts/ui_manager.py
# v4

import time
import logging
from enum import Enum, auto
from PIL import ImageChops

logger = logging.getLogger("UIManager")

from ui_screen_main import MainUIRenderer
from ui_screen_info import InfoScreenRenderer
from ui_screen_saver import ScreenSaverRenderer
from ui_status_bar import StatusBarRenderer
from ui_screen_photo import PhotoScreenRenderer
from ui_screen_mask import MaskScreenRenderer
from ui_volume_popup import VolumePopupRenderer
from ui_screen_assistant import AssistantScreenRenderer
from ui_screen_reboot import RebootScreenRenderer


class Overlay(Enum):
    NONE = auto()
    MASK = auto()
    VOLUME = auto()
    INFO = auto()
    PHOTO = auto()
    ASSISTANT = auto()
    REBOOT = auto()


class UIManager:
    """
    UI 渲染引擎与屏幕管家：
    接管所有的界面流转、动画超时逻辑，以及最高效的 ImageChops 局部脏矩形渲染机制。

    浮层状态通过 Overlay 枚举互斥管理，从语言层面保证同一时刻只存在一个浮层。
    """
    def __init__(self, display_ctx, cfg):
        self.display_ctx = display_ctx
        self.cfg = cfg

        # 1. 实例化各个子屏幕渲染器
        self.ui_main       = MainUIRenderer(display_ctx, cfg.get("ui", {}))
        self.ui_info       = InfoScreenRenderer(display_ctx, cfg.get("ui", {}))
        self.ui_saver      = ScreenSaverRenderer(display_ctx, cfg.get("ui", {}))
        self.ui_status_bar = StatusBarRenderer(display_ctx, cfg.get("ui", {}))
        self.ui_photo      = PhotoScreenRenderer(display_ctx, cfg.get("ui", {}))
        self.ui_mask       = MaskScreenRenderer(display_ctx, cfg.get("ui", {}))
        self.ui_volume     = VolumePopupRenderer(display_ctx, cfg.get("ui", {}))
        self.ui_assistant  = AssistantScreenRenderer(display_ctx, cfg.get("ui", {}))
        self.ui_reboot     = RebootScreenRenderer(display_ctx, cfg.get("ui", {}))

        # 2. 浮层状态：单一枚举变量，强制互斥
        self.active_overlay = Overlay.NONE
        self.overlay_timer = 0.0

        # 3. 按钮高亮状态
        self.active_button = None
        self.active_button_timer = 0.0
        self.mask_exit_at = 0.0
        self.MASK_HIGHLIGHT_DURATION = 0.35

        # 4. 音量显示（点击式，无拖拽）
        self.current_display_volume = 50

        # 5. 弹窗自动关闭时间
        self.popup_duration = cfg.get("popup", {}).get("duration", 3.0)

        # 6. 进度条拖拽状态：None 表示未拖拽，float 表示拖拽中的比例值
        self.drag_progress_ratio: float | None = None

        # 7. 渲染缓存与性能统计
        self.last_screen_img = None
        self.fps = 0.0
        self.spi_time_ms = 0.0
        self.frame_count = 0
        self.last_fps_calc_time = time.time()

        # 8. 屏保刷新节拍（替代 render_key）
        self._last_saver_second = -1

        # 9. Assistant 状态
        self.voice_state = "idle"
        self.transcript_text = ""

        # 10. 对话历史（每次 awake-done 为一轮）
        # [{"user": str, "assistant": str, "state": str}, ...]
        self.conversation_history = []
        self.assistant_close_at   = 0.0   # 非零时表示定时关闭

    # ── 对外接口：供 InputController 查询当前 UI 状态 ──────────────────────

    def get_ui_state_dict(self, player_state=None):
        """暴露给 InputController 用于触摸判断的当前状态"""
        is_playing = player_state is not None and not player_state.is_clock
        return {
            "active_overlay": self.active_overlay,
            "dragging_progress": self.drag_progress_ratio is not None,
            "drag_progress_ratio": self.drag_progress_ratio,
            "is_clock_screen": not is_playing
                               and self.active_overlay == Overlay.NONE,
            "time_total": player_state.time_total if player_state else 0.0,
        }

    # ── 动作处理 ────────────────────────────────────────────────────────────

    def handle_action(self, action, current_time, player_state):
        """处理从 InputController 解析出的动作"""
        if not action:
            return
        act_type = action.get("type")

        if act_type == "SHOW_VOLUME":
            self.active_overlay = Overlay.VOLUME
            self.overlay_timer = current_time
            vol_raw = player_state.volume if player_state and player_state.volume >= 0 else 50
            self.current_display_volume = max(0, min(100, vol_raw))

        elif act_type == "CLOSE_VOLUME":
            if self.active_overlay == Overlay.VOLUME:
                self.active_overlay = Overlay.NONE

        # 音量点击：设置值并立即关闭弹窗（无拖拽）
        elif act_type == "SET_VOLUME_AND_CLOSE":
            self.current_display_volume = action.get("value", self.current_display_volume)
            self.active_overlay = Overlay.NONE

        # 进度条拖拽（视觉预览 + 节流指令）
        elif act_type in ("DRAG_PROGRESS_VISUAL", "DRAG_PROGRESS_ACTION"):
            self.drag_progress_ratio = action.get("value")

        elif act_type == "SET_PROGRESS":
            self.drag_progress_ratio = None

        elif act_type == "SHOW_INFO":
            self.active_overlay = Overlay.INFO
            self.overlay_timer = current_time
            self.active_button = "info"
            self.active_button_timer = current_time

        elif act_type == "CLOSE_INFO":
            if self.active_overlay == Overlay.INFO:
                self.active_overlay = Overlay.NONE
                self.active_button = None

        elif act_type == "SYSTEM_REBOOT":
            import subprocess
            logger.info("Reboot requested via UI. Executing sudo reboot...")
            self.active_overlay = Overlay.REBOOT
            self.overlay_timer = current_time
            subprocess.Popen(["sudo", "reboot"])

        elif act_type == "SHOW_PHOTO":
            self.active_overlay = Overlay.PHOTO
            self.overlay_timer = current_time
            self.active_button = None

        elif act_type == "CLOSE_PHOTO":
            if self.active_overlay == Overlay.PHOTO:
                self.active_overlay = Overlay.NONE

        elif act_type == "SHOW_MASK":
            self.active_overlay = Overlay.MASK
            self.overlay_timer = current_time
            self.active_button = None

        elif act_type == "CLOSE_MASK":
            if self.active_overlay == Overlay.MASK:
                self.active_overlay = Overlay.NONE
                self.active_button = None
                self.mask_exit_at = 0.0

        elif act_type == "MASK_CLICK":
            self.active_button = action.get("button")
            self.active_button_timer = current_time
            self.mask_exit_at = current_time + self.MASK_HIGHLIGHT_DURATION
            self.overlay_timer = current_time

        elif act_type == "SHOW_ASSISTANT":
            self.active_overlay      = Overlay.ASSISTANT
            self.voice_state         = action.get("voice_state", "idle")
            self.transcript_text     = action.get("transcript", "")
            self.conversation_history = action.get("history", [])
            self.overlay_timer       = current_time
            self.assistant_close_at  = action.get("close_at", 0.0)

        elif act_type == "CLOSE_ASSISTANT":
            self.active_overlay      = Overlay.NONE  # 马上关闭助手，不等待超时
            self.voice_state         = "idle"
            self.transcript_text     = ""
            self.conversation_history = []
            self.assistant_close_at  = 0.0

    def dismiss_screens_on_play(self):
        """当从空闲切入播放状态时，清理所有浮层"""
        self.active_overlay = Overlay.NONE
        self.active_button = None
        self.mask_exit_at = 0.0
        self.drag_progress_ratio = None

    # ── 超时处理 ─────────────────────────────────────────────────────────────

    def update_timeouts(self, current_time):
        """处理弹窗、遮罩等自动关闭超时逻辑"""
        if self.active_overlay == Overlay.MASK:
            # 蒙板：正常超时，或按钮高亮结束后立即退出
            if self.mask_exit_at > 0 and current_time >= self.mask_exit_at:
                self.active_overlay = Overlay.NONE
                self.active_button = None
                self.mask_exit_at = 0.0
            elif current_time - self.overlay_timer >= self.popup_duration:
                self.active_overlay = Overlay.NONE
                self.active_button = None
                self.mask_exit_at = 0.0

        elif self.active_overlay == Overlay.VOLUME:
            if current_time - self.overlay_timer >= self.popup_duration:
                self.active_overlay = Overlay.NONE

        elif self.active_overlay == Overlay.ASSISTANT:
            if self.assistant_close_at > 0 and current_time >= self.assistant_close_at:
                self.active_overlay = Overlay.NONE
                self.voice_state    = "idle"
                self.transcript_text = ""
                self.conversation_history = []
                self.assistant_close_at   = 0.0

        # 按钮高亮短暂显示后清除
        if self.active_button and (current_time - self.active_button_timer >= 0.2):
            self.active_button = None

    # ── 核心渲染 ─────────────────────────────────────────────────────────────

    def render_frame(self, current_time, player_state, system_info, services_status,
                     screen_saver, playing_transition, is_playing):
        """核心画面生成与局部差异刷新 (Dirty Rectangle)"""

        # 更新 FPS 统计
        if current_time - self.last_fps_calc_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_fps_calc_time)
            self.frame_count = 0
            self.last_fps_calc_time = current_time

        # 保持内部音量变量与后台实际音量同步
        if player_state and player_state.volume >= 0:
            self.current_display_volume = max(0, min(100, player_state.volume))

        # ── 决定是否需要渲染本帧 ──────────────────────────────────────────
        if screen_saver.is_off and not is_playing:
            # 屏幕关闭且无播放，跳过渲染
            return

        if is_playing or playing_transition or self.active_overlay == Overlay.ASSISTANT:
            # 播放中或处于助手状态：始终渲染（跑马灯滚动、进度条推进、语音动画需要连续帧）
            should_render = True
        else:
            # 屏保（时钟）：每秒刷新一次即可
            current_second = int(current_time)
            should_render = (current_second != self._last_saver_second)
            if should_render:
                self._last_saver_second = current_second

        # 浮层状态变化也需要立即渲染（通过 last_screen_img 为 None 的初始化情况覆盖）
        # 注意：overlay 切换时 should_render 可能恰好为 False（屏保路径下）
        # 但因为播放中始终渲染，实际上 overlay 只在 is_playing 时出现，无需额外处理

        if not should_render:
            return

        t_start = time.time()
        img = None

        # ── 构建画面 ─────────────────────────────────────────────────────────
        overlay = self.active_overlay

        if overlay == Overlay.INFO:
            if screen_saver.is_off:
                screen_saver.wake()
            system_info['fps'] = self.fps
            system_info['spi_time_ms'] = self.spi_time_ms
            img = self.ui_info.render(system_info, services_status)
            img = self.ui_status_bar.render(img, player_state, self.active_button,
                                            current_screen="info")

        elif overlay == Overlay.PHOTO:
            if screen_saver.is_off:
                screen_saver.wake()
            img = self.ui_photo.render(player_state)

        elif overlay == Overlay.REBOOT:
            if screen_saver.is_off:
                screen_saver.wake()
            img = self.ui_reboot.render()

        elif not is_playing:
            # 屏保时钟
            img = self.ui_saver.render(
                time.strftime("%H:%M"),
                time.strftime("%A, %B %d"),
                screen_saver.is_dimmed
            )

        else:
            # 主播放界面
            img = self.ui_main.render(player_state)

            if overlay == Overlay.MASK:
                img = self.ui_mask.render(img, player_state, self.active_button)

            if self.cfg.get("ui", {}).get("screens", {}).get("main", {}).get(
                    "show_status_bar", True):
                img = self.ui_status_bar.render(img, player_state, self.active_button,
                                                current_screen="main")

            if overlay == Overlay.VOLUME:
                img = self.ui_volume.render(img, self.current_display_volume)
                
        if overlay == Overlay.ASSISTANT:
            img = self.ui_assistant.render(
                img, self.voice_state, self.transcript_text,
                self.conversation_history
            )

        # ── SPI 发送（脏区差异刷新）────────────────────────────────────────
        if img:
            if self.last_screen_img is None or playing_transition:
                self.display_ctx['device'].show_image(img)
            else:
                diff = ImageChops.difference(img, self.last_screen_img)
                bbox = diff.getbbox()
                if bbox:
                    cropped = img.crop(bbox)
                    if hasattr(self.display_ctx['device'], 'show_image_partial'):
                        self.display_ctx['device'].show_image_partial(
                            cropped, bbox[0], bbox[1])
                    else:
                        self.display_ctx['device'].show_image(img)

            self.last_screen_img = img.copy()
            self.spi_time_ms = (time.time() - t_start) * 1000
            self.frame_count += 1
