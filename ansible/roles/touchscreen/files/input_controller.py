#!/usr/bin/env python
# resources/ts/input_controller.py
# v2

import threading
import subprocess
import logging
from query_source import get_player_status
import time
from ui_volume_popup import VolumePopupRenderer
from ui_manager import Overlay

logger = logging.getLogger("InputController")

class InputController:
    """
    输入路由器：将原始 X/Y 坐标解析为语义化的 UI 动作 (Action)。
    并管理由输入触发的独立后台硬件指令。
    """
    def __init__(self, config, display_ctx, lms_params, pactl_env):
        self.config = config
        self.display_ctx = display_ctx
        self.lms_params = lms_params
        self.pactl_env = pactl_env
        self.status_bar_height = config.get("ui", {}).get("screens", {}).get(
            "status_top", {}).get("height", 60)

        self.screen_w = display_ctx["width"]
        self.screen_h = display_ctx["height"]

        # 进度条跳转节流阀
        self.last_seek_cmd_time = 0

    def get_semantic_action(self, touch_type, x, y, ui_state):
        """
        解析坐标，返回语义化动作。
        ui_state: get_ui_state_dict() 返回的字典
        """
        active_overlay = ui_state.get("active_overlay", Overlay.NONE)
        is_dragging_prog = ui_state.get("dragging_progress", False)
        is_clock_screen = ui_state.get("is_clock_screen", False)

        # ── 0. 全局导航层（仅响应 DOWN）────────────────────────────────────
        if touch_type == "DOWN":
            if active_overlay == Overlay.INFO:
                if 420 <= x <= 480 and 50 <= y <= 110:
                    return {"type": "SYSTEM_REBOOT"}
                return {"type": "CLOSE_INFO"}
            if active_overlay == Overlay.PHOTO:
                return {"type": "CLOSE_PHOTO"}
            if is_clock_screen:
                return {"type": "SHOW_INFO"}

        # ── 1. 音量弹窗（点击式，无拖拽）───────────────────────────────────
        if active_overlay == Overlay.VOLUME:
            if touch_type != "DOWN":
                return None

            pw = VolumePopupRenderer.POPUP_W
            ph = VolumePopupRenderer.POPUP_H
            mb = VolumePopupRenderer.MARGIN_BOTTOM
            icon_w = VolumePopupRenderer.ICON_AREA_W
            pct_w = VolumePopupRenderer.PCT_AREA_W

            p_x = (self.screen_w - pw) // 2
            p_y = self.screen_h - ph - mb
            bar_x = p_x + icon_w
            bar_w = pw - icon_w - pct_w

            # 点击滑条区域：计算对应音量并关闭弹窗
            in_bar_zone = (
                bar_x - 20 <= x <= bar_x + bar_w + 20
                and p_y - 20 <= y <= p_y + ph + 20
            )
            if in_bar_zone:
                ratio = (x - bar_x) / bar_w
                new_vol = int(max(0.0, min(1.0, ratio)) * 100)
                return {"type": "SET_VOLUME_AND_CLOSE", "value": new_vol}

            # 点击弹窗外：关闭弹窗
            if not (p_x <= x <= p_x + pw and p_y <= y <= p_y + ph):
                return {"type": "CLOSE_VOLUME"}

            # 点击弹窗内非滑条区域：消费事件，防止穿透
            return None

        # ── 2. MASK 拦截（次顶层）─────────────────────────────────────────
        if active_overlay == Overlay.MASK:
            if touch_type != "DOWN":
                return None
            if y > self.status_bar_height:
                section_w = self.screen_w // 3
                if 0 <= x < section_w:
                    return {"type": "MASK_CLICK", "button": "prev"}
                elif section_w <= x < section_w * 2:
                    return {"type": "MASK_CLICK", "button": "play_pause"}
                else:
                    return {"type": "MASK_CLICK", "button": "next"}
            # 点击状态栏区域也关闭蒙板
            return {"type": "CLOSE_MASK"}

        # ── 3. 进度条热区 ────────────────────────────────────────────────────
        pb_cfg = self.config.get("screens", {}).get("main", {}).get("progress_bar", {})
        pb_x, pb_y = pb_cfg.get("pos", [20, 262])
        pb_w = pb_cfg.get("width", 440)

        in_prog_zone = (
            pb_y - 25 <= y <= pb_y + 30
            and pb_x - 15 <= x <= pb_x + pb_w + 15
        )

        time_tot = ui_state.get("time_total", 0.0)
        # 如果总时长为0（如 AirPlay/Bluetooth），则直接锁定进度条，不允许拖拽
        if time_tot > 0 and (is_dragging_prog or (touch_type == "DOWN" and in_prog_zone)):
            if touch_type == "UP":
                ratio = ui_state.get("drag_progress_ratio", 0.0) or 0.0
                return {"type": "SET_PROGRESS", "value": ratio}

            ratio = max(0.0, min(1.0, (x - pb_x) / pb_w))
            if touch_type == "DOWN":
                return {"type": "DRAG_PROGRESS_VISUAL", "value": ratio}
            # MOVE：只更新前端视觉比例，绝对不发送后台硬件指令，防止 LMS 服务器/播放器因为高频 Seek 彻底卡死
            return {"type": "DRAG_PROGRESS_VISUAL", "value": ratio}

        # 手指滑出热区后抬起，正确结束拖拽
        if touch_type == "UP" and is_dragging_prog:
            return {"type": "SET_PROGRESS",
                    "value": ui_state.get("drag_progress_ratio", 0.0) or 0.0}

        # ── 静态按钮仅响应 DOWN ──────────────────────────────────────────────
        if touch_type != "DOWN":
            return None

        # ── 4. 状态栏热区 ────────────────────────────────────────────────────
        if 10 < y < 50:
            if 75 < x < 130:
                return {"type": "SHOW_VOLUME"}
            elif 130 < x < 190:
                return {"type": "SHOW_INFO"}
            elif 320 < x < 390:
                return {"type": "SHOW_PHOTO"}

        # ── 5. 默认：呼出控制蒙板 ────────────────────────────────────────────
        return {"type": "SHOW_MASK"}

    def execute_volume_cmd(self, player_state, new_vol):
        """在后台独立线程中执行音量调节指令，防止阻塞 UI"""
        player_type = getattr(player_state, "active_player_type", None) if player_state else None

        def _do_set():
            try:
                if player_type == "squeezelite":
                    get_player_status(
                        ["mixer", "volume", str(new_vol)],
                        self.lms_params["host_ip"],
                        self.lms_params["host_port"],
                        self.lms_params["player_id"]
                    )
                else:
                    subprocess.run(
                        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{new_vol}%"],
                        env=self.pactl_env, timeout=1
                    )
            except Exception as e:
                logger.warning(f"Execute volume cmd failed (type={player_type}): {e}")

        threading.Thread(target=_do_set, daemon=True).start()

    def execute_player_cmd(self, player_state, action):
        """在后台独立线程中执行播放器控制指令"""
        if not player_state:
            return
        player_type = player_state.active_player_type
        logger.info(f"Player command triggered for {player_type}: {action}")

        if player_type == "squeezelite":
            cmd = []
            if action == "prev":         cmd = ["button", "jump_rew"]
            elif action == "next":       cmd = ["button", "jump_fwd"]
            elif action == "play_pause": cmd = ["pause"]
            elif action == "pause":      cmd = ["pause", "1"]  # 强制暂停
            elif action == "play":       cmd = ["pause", "0"]  # 强制播放
            
            if cmd:
                threading.Thread(
                    target=get_player_status,
                    args=(cmd, self.lms_params["host_ip"],
                          self.lms_params["host_port"],
                          self.lms_params["player_id"]),
                    daemon=True
                ).start()

        elif player_type == "bluetooth":
            dbus_action = ""
            if action == "prev":         dbus_action = "Previous"
            elif action == "next":       dbus_action = "Next"
            elif action == "play_pause": dbus_action = "PlayPause"

            if dbus_action:
                def _do_dbus_cmd():
                    try:
                        import pydbus
                        bus = pydbus.SystemBus()
                        manager = bus.get('org.bluez', '/')
                        managed_objects = manager.GetManagedObjects()
                        player_path = None
                        for path, interfaces in managed_objects.items():
                            if 'org.bluez.MediaPlayer1' in interfaces:
                                player_path = path
                                break
                    except Exception as e:
                        logger.warning(f"pydbus player lookup failed: {e}")
                        player_path = None

                    if not player_path:
                        try:
                            import re, subprocess as sp
                            cmd = ["dbus-send", "--system", "--print-reply",
                                   "--dest=org.bluez", "/",
                                   "org.freedesktop.DBus.ObjectManager.GetManagedObjects"]
                            output = sp.check_output(cmd, timeout=1).decode()
                            m = re.search(
                                r'object path "(/org/bluez/hci[0-9]*/dev_[^"]+/player\d+)"',
                                output, re.IGNORECASE)
                            if m:
                                player_path = m.group(1)
                        except Exception as e:
                            logger.warning(f"dbus-send fallback failed: {e}")

                    if player_path:
                        try:
                            subprocess.run(
                                ["dbus-send", "--system", "--print-reply",
                                 "--dest=org.bluez", player_path,
                                 f"org.bluez.MediaPlayer1.{dbus_action}"],
                                stderr=subprocess.DEVNULL, timeout=1
                            )
                        except Exception as e:
                            logger.warning(f"DBus command failed: {e}")
                    else:
                        logger.warning("Could not find active DBus media player.")

                threading.Thread(target=_do_dbus_cmd, daemon=True).start()
                
        elif player_type == "airplay":
            mpris_action = ""
            if action == "prev":         mpris_action = "Previous"
            elif action == "next":       mpris_action = "Next"
            elif action == "play_pause": mpris_action = "PlayPause"
            
            if mpris_action:
                def _do_airplay_cmd():
                    try:
                        # AirPlay (Shairport-sync) 使用标准的 MPRIS D-Bus 接口进行控制
                        import subprocess
                        subprocess.run(
                            ["dbus-send", "--system", "--print-reply",
                             "--dest=org.mpris.MediaPlayer2.shairport-sync", 
                             "/org/mpris/MediaPlayer2",
                             f"org.mpris.MediaPlayer2.Player.{mpris_action}"],
                            stderr=subprocess.DEVNULL, timeout=1
                        )
                    except Exception as e:
                        logger.warning(f"AirPlay MPRIS command failed: {e}")
                
                threading.Thread(target=_do_airplay_cmd, daemon=True).start()

    def execute_seek_cmd(self, player_state, ratio):
        """在后台执行进度条跳转指令"""
        if (player_state
                and player_state.active_player_type == "squeezelite"
                and player_state.time_total > 0):
            target_time = int(player_state.time_total * ratio)
            logger.info(f"Seek track to: {target_time}s")
            threading.Thread(
                target=get_player_status,
                args=(["time", str(target_time)],
                      self.lms_params["host_ip"],
                      self.lms_params["host_port"],
                      self.lms_params["player_id"]),
                daemon=True
            ).start()
