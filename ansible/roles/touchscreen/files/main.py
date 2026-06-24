#!/usr/bin/env python
# resources/ts/main.py
# v5

import time
import sys
import threading
import logging
import signal
import subprocess

from config import load_config
from hardware_display import init_display, turn_off_display
from query_source import setup_pactl_env, init_airplay_pipe
from screensaver import ScreenSaver

from ft6336u import ft6336u
from state_manager import StateManager
from input_controller import InputController
from ui_manager import UIManager
from assistant_listener import AssistantListener

# ============================================
# 全局配置参数
# ============================================
TOUCH_DEBOUNCE_TIME = 0.15  # 触摸防抖/冷却时间 (秒)

# ============================================
# 初始化日志配置（临时使用 INFO 级别）
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Main")


def main():
    def sigterm_handler(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, sigterm_handler)

    try:
        # ============================================
        # 1. 加载配置
        # ============================================
        cfg = load_config()

        # 重新配置日志级别（使用配置文件中的设置）
        log_level = cfg["ts"]["log_level"]
        logging.getLogger().setLevel(log_level)
        logger.info(f"日志级别已设置为: {logging.getLevelName(log_level)}")

        lms_params = {
            "host_ip":   cfg["lms"]["host_ip"],
            "host_port": cfg["lms"]["host_port"],
            "player_id": cfg["lms"]["player_id"],
        }

        # ============================================
        # 2. 初始化环境
        # ============================================
        display_ctx = init_display(
            ts_config=cfg["ts"],
            display_config=cfg["display"]
        )

        # ============================================
        # 2.5 播放开机动画 (Terminator Boot)
        # ============================================
        from ui_boot_animation import play_boot_animation
        play_boot_animation(display_ctx, cfg["ui"].get("boot_animation", {}))

        # ============================================
        # 3. 初始化触摸屏
        # ============================================
        try:
            touch = ft6336u()
        except NameError:
            touch = None

        # ============================================
        # 3.2 准备底层环境 (后台并行初始化)
        # ============================================
        # setup_pactl_env and init_airplay_pipe shouldn't block the screen
        pactl_env = setup_pactl_env()

        airplay_cfg = cfg.get("airplay", {})
        pipe_path = airplay_cfg.get("metadata_pipe", "/tmp/shairport-sync-metadata")
        init_airplay_pipe(pipe_path)
        
        screen_saver = ScreenSaver(
            display_ctx,
            idle_dim_timeout=cfg["screensaver"]["idle_dim_timeout"],
            media_dim_timeout=cfg["screensaver"]["media_dim_timeout"],
            off_timeout=cfg["screensaver"]["off_timeout"]
        )

        # ============================================
        # 3.3 等待网络与 LMS 服务器就绪
        # ============================================
        import socket
        from PIL import Image, ImageDraw, ImageFont

        logger.info(f"等待网络和 LMS 服务器 ({lms_params['host_ip']}:{lms_params['host_port']}) 就绪...")
        
        # 准备“网络等待”画面
        device = display_ctx["device"]
        w = display_ctx["width"]
        h = display_ctx["height"]
        
        if "ui" not in cfg or "boot_animation" not in cfg["ui"] or "global" not in cfg["ui"]:
            logger.error("Missing ui config. Exiting.")
            sys.exit(1)

        boot_cfg = cfg["ui"]["boot_animation"]
        global_cfg = cfg["ui"]["global"]
        
        if "network_wait_text1" not in boot_cfg or "network_wait_text3" not in boot_cfg or "font_main" not in global_cfg:
            logger.error("Missing necessary ui config items. Exiting.")
            sys.exit(1)

        if "network_wait_color" not in boot_cfg:
            logger.error("Missing network_wait_color. Exiting.")
            sys.exit(1)

        t1_cfg = boot_cfg["network_wait_text1"]
        t3_cfg = boot_cfg["network_wait_text3"]
        
        if not isinstance(t1_cfg, dict) or not isinstance(t3_cfg, dict):
            logger.error("network_wait_text1 and 3 must be dictionaries. Exiting.")
            sys.exit(1)
            
        if "text" not in t1_cfg or "font_size" not in t1_cfg or "text" not in t3_cfg or "font_size" not in t3_cfg:
            logger.error("Missing text or font_size in network_wait text configs. Exiting.")
            sys.exit(1)

        wait_text1 = t1_cfg["text"]
        wait_text3 = t3_cfg["text"]
        
        size1 = t1_cfg["font_size"]
        size3 = t3_cfg["font_size"]
        
        pos1 = t1_cfg.get("pos")
        pos3 = t3_cfg.get("pos")

        wait_color = tuple(boot_cfg["network_wait_color"])
        font_path = global_cfg["font_main"]

        try:
            font1 = ImageFont.truetype(font_path, size1)
            font3 = ImageFont.truetype(font_path, size3)
        except Exception as e:
            logger.error(f"Failed to load fonts from {font_path}: {e}")
            sys.exit(1)

        wait_img = Image.new("RGB", (w, h), (0, 0, 0))
        draw = ImageDraw.Draw(wait_img)

        def get_text_size(text, font):
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                return bbox[2] - bbox[0], bbox[3] - bbox[1]
            except AttributeError:
                return draw.textsize(text, font=font)

        w1, h1 = get_text_size(wait_text1, font1)
        w3, h3 = get_text_size(wait_text3, font3)
        
        h2 = 20 # Empty line height
        total_h = h1 + h2 + h3
        auto_start_y = (h - total_h) // 2
        
        draw_pos1 = tuple(pos1) if pos1 else ((w - w1) // 2, auto_start_y)
        draw_pos3 = tuple(pos3) if pos3 else ((w - w3) // 2, auto_start_y + h1 + h2)

        draw.text(draw_pos1, wait_text1, font=font1, fill=wait_color)
        draw.text(draw_pos3, wait_text3, font=font3, fill=wait_color)

        device.show_image(wait_img)

        while True:
            try:
                with socket.create_connection((lms_params["host_ip"], lms_params["host_port"]), timeout=2.0):
                    logger.info("网络和 LMS 服务器已就绪！")
                    break
            except OSError:
                time.sleep(0.5)

        state_mgr = StateManager(pactl_env, lms_params, touch)
        state_mgr.start_background_threads()

        input_ctrl = InputController(cfg, display_ctx, lms_params, pactl_env)
        ui_mgr = UIManager(display_ctx, cfg)

        # ============================================
        # 3.5 初始化并启动语音助手监听器
        # ============================================
        assistant_listener = AssistantListener()
        assistant_listener.start()

        # 注册截屏信号监听器 (SIGUSR1)
        def sigusr1_handler(signum, frame):
            if getattr(ui_mgr, 'last_screen_img', None):
                filename = f"/tmp/screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
                ui_mgr.last_screen_img.save(filename)
                logger.info(f"📸 截屏已保存至: {filename}")
        signal.signal(signal.SIGUSR1, sigusr1_handler)

        logger.info("System Ready - Starting UI Loop")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

    # ============================================
    # 4. 主循环
    # ============================================
    was_playing = False
    last_touch_time = 0.0
    last_player_signature = None

    while True:
        try:
            current_time = time.time()

            player_state, system_info, services_status = state_mgr.get_app_state()

            # ── 消费触摸事件 ──────────────────────────────────────────────────
            while True:
                evt = state_mgr.get_touch_event()
                if not evt:
                    break

                screen_saver.wake()
                touch_type, x, y = evt

                action = input_ctrl.get_semantic_action(
                    touch_type, x, y,
                    ui_mgr.get_ui_state_dict(player_state)
                )

                if action:
                    # DOWN 事件应用防抖
                    if touch_type == "DOWN" and (
                            current_time - last_touch_time < TOUCH_DEBOUNCE_TIME):
                        continue
                    last_touch_time = current_time

                    ui_mgr.handle_action(action, current_time, player_state)
                    act_type = action.get("type")

                    # 执行后台硬件指令
                    if act_type == "SET_VOLUME_AND_CLOSE":
                        input_ctrl.execute_volume_cmd(player_state, action.get("value"))
                    elif act_type in ("SET_PROGRESS", "DRAG_PROGRESS_ACTION"):
                        input_ctrl.execute_seek_cmd(player_state, action.get("value"))
                    elif act_type == "MASK_CLICK":
                        input_ctrl.execute_player_cmd(player_state, action.get("button"))

            # ── 消费语音助手事件 ──────────────────────────────────────────────
            while True:
                ast_evt = assistant_listener.get_event()
                if not ast_evt:
                    break

                screen_saver.wake()
                evt_type = ast_evt.get("event")

                # 让 state_manager 全权处理跨域状态逻辑
                voice_session = state_mgr.advance_voice_state(ast_evt)

                # main 只负责消费：如果是新发起的唤醒，且原先在播放，则暂停
                if evt_type == "awake":
                    if voice_session.is_active and voice_session.was_playing_before_voice:
                        is_playing_now = (player_state is not None
                                      and not getattr(player_state, "is_paused", True)
                                      and not getattr(player_state, "is_clock", False))
                        if is_playing_now:
                            input_ctrl.execute_player_cmd(player_state, "pause")

                if evt_type in ("done", "timeout", "error"):
                    action_type = "CLOSE_ASSISTANT"
                else:
                    action_type = "SHOW_ASSISTANT"

                ui_mgr.handle_action(
                    {
                        "type": action_type,
                        "voice_state": voice_session.voice_state,
                        "transcript": voice_session.transcript_text,
                        "history": voice_session.history,
                        "close_at": voice_session.close_at,
                    },
                    current_time,
                    player_state,
                )

                # 消费完毕：如果是结束状态，且原先在播放，则恢复播放
                if evt_type in ("done", "timeout", "error"):
                    if voice_session.was_playing_before_voice:
                        input_ctrl.execute_player_cmd(player_state, "play")

            # ── 播放状态判断 ──────────────────────────────────────────────────
            is_playing = player_state is not None and not getattr(player_state, "is_clock", False)
            current_signature = getattr(player_state, "signature", None) if player_state else None

            # ── 检查语音助手超时兜底 ──────────────────────────────────────────
            vs = state_mgr.get_voice_session()
            if vs.voice_state != "idle" and vs.close_at > 0 and current_time >= vs.close_at:
                timeout_session = state_mgr.advance_voice_state({"event": "timeout"})
                ui_mgr.handle_action(
                    {
                        "type": "CLOSE_ASSISTANT",
                        "voice_state": timeout_session.voice_state,
                        "transcript": timeout_session.transcript_text,
                        "history": timeout_session.history,
                        "close_at": timeout_session.close_at,
                    },
                    current_time,
                    player_state,
                )
                if timeout_session.was_playing_before_voice:
                    input_ctrl.execute_player_cmd(player_state, "play")

            # ── 弹窗超时处理 ──────────────────────────────────────────────────
            ui_mgr.update_timeouts(current_time)

            playing_transition = is_playing and not was_playing
            idle_transition = not is_playing and was_playing
            track_changed = (
                is_playing
                and last_player_signature is not None
                and current_signature != last_player_signature
            )

            # 状态切换时唤醒屏幕
            if playing_transition or idle_transition or track_changed:
                screen_saver.wake()
                if playing_transition:
                    ui_mgr.dismiss_screens_on_play()

            was_playing = is_playing
            last_player_signature = current_signature

            # ── 屏保心跳 ──────────────────────────────────────────────────────
            screen_saver.tick(is_playing)

            # ── 拖拽进度条时实时篡改播放位置（视觉预览）─────────────────────
            if ui_mgr.drag_progress_ratio is not None:
                if player_state and player_state.time_total > 0:
                    player_state.time_current = (
                        player_state.time_total * ui_mgr.drag_progress_ratio
                    )

            # ── 核心渲染 ──────────────────────────────────────────────────────
            ui_mgr.render_frame(
                current_time, player_state, system_info, services_status,
                screen_saver, playing_transition, is_playing
            )

            time.sleep(0.03)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Main Loop Error: {e}")
            time.sleep(1)

    # ── 退出清理 ──────────────────────────────────────────────────────────────
    try:
        if 'assistant_listener' in locals():
            assistant_listener.stop()

        from PIL import Image
        if 'display_ctx' in locals() and 'device' in display_ctx:
            display_ctx['device'].show_image(
                Image.new("RGB", (display_ctx['width'], display_ctx['height']), "BLACK")
            )
        if 'display_ctx' in locals():
            turn_off_display(display_ctx)
    except Exception as e:
        logger.error(f"Exit cleanup error: {e}")


if __name__ == "__main__":
    main()