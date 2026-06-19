#!/usr/bin/env python
# resources/ts/screensaver.py

import time
import logging

# 导入显示控制函数
from hardware_display import (
    set_brightness, 
    turn_off_display,
    turn_on_display,
    restore_brightness
)

class ScreenSaver:
    def __init__(self, display_ctx, idle_dim_timeout=10, media_dim_timeout=60, off_timeout=900):
        """
        初始化屏幕保护管理器
        :param display_ctx: 显示上下文 (包含 device 对象)
        :param idle_dim_timeout: 待机空闲变暗超时 (秒)
        :param media_dim_timeout: 播放状态变暗超时 (秒)
        :param off_timeout: 关闭超时时间 (秒)
        """
        self.ctx = display_ctx
        self.idle_dim_timeout = idle_dim_timeout
        self.media_dim_timeout = media_dim_timeout
        self.off_timeout = off_timeout
        
        self.last_activity = time.time()
        self.is_dimmed = False
        self.is_off = False
        self._current_dim_level = None
        
        # 从上下文获取亮度设置
        self.default_brightness = display_ctx["default_brightness"]
        self.dim_brightness = display_ctx["dim_brightness"]
        self.media_dim_brightness = display_ctx.get("media_dim_brightness", 32)
        
        # 初始状态：确保屏幕是亮着的
        self.wake()

    def wake(self):
        """唤醒屏幕（用户有操作或状态改变时调用）"""
        self.last_activity = time.time()
        
        # 如果屏幕已关闭，打开它
        if self.is_off:
            try:
                turn_on_display(self.ctx)
                self.is_off = False
                logging.info("ScreenSaver: Screen ON")
            except Exception as e:
                logging.error(f"ScreenSaver error (wake/on): {e}")

        # 如果屏幕已变暗，恢复亮度
        if self.is_dimmed:
            try:
                restore_brightness(self.ctx)
                self.is_dimmed = False
                self._current_dim_level = None
                logging.info("ScreenSaver: Brightness RESTORED")
            except Exception as e:
                logging.error(f"ScreenSaver error (wake/bright): {e}")

    def tick(self, is_media_active=False):
        """
        心跳检查（需在主循环中定期调用）
        :param is_media_active: 当前是否有媒体正在播放或暂停 (True: 播放/暂停, False: 停止/空闲)
        """
        elapsed = time.time() - self.last_activity
        
        # 根据当前状态确定对应的超时时间
        current_timeout = self.media_dim_timeout if is_media_active else self.idle_dim_timeout

        # 检查是否需要变暗，或者切换变暗等级
        if elapsed > current_timeout:
            # 播放时超时变暗到配置的媒体亮度，空闲时变暗到配置的极暗亮度
            target_dim = self.media_dim_brightness if is_media_active else self.dim_brightness
            if not self.is_dimmed or getattr(self, '_current_dim_level', None) != target_dim:
                try:
                    set_brightness(self.ctx, target_dim)
                    self.is_dimmed = True
                    self._current_dim_level = target_dim
                    logging.info(f"ScreenSaver: Screen DIMMED to {target_dim}")
                except Exception as e:
                    logging.error(f"ScreenSaver error (dim): {e}")
        
        # 检查是否需要关闭
        # 只有在 media inactive (is_media_active=False) 状态下，且超时后，才允许屏幕关闭。
        if not self.is_off and elapsed > self.off_timeout and not is_media_active:
            try:
                turn_off_display(self.ctx)
                self.is_off = True
                logging.info("ScreenSaver: Screen OFF")
            except Exception as e:
                logging.error(f"ScreenSaver error (off): {e}")
