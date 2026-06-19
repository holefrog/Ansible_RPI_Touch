#!/usr/bin/env python
# resources/ts/state_handlers.py

import time
import os
from query_source import (
    update_airplay_metadata, get_system_volume,
    get_bluetooth_metadata, get_bluetooth_volume_dbus,
    get_player_status, extract_result_field, check_bluetooth_connected,
    download_cover
)

_last_cover_signature = None

def _process_lms_cover(state, lms_config):
    """处理 LMS 封面下载和设置逻辑"""
    global _last_cover_signature
    
    # 查询是否存在真实封面
    _, res_status = get_player_status(["status", "-", "1", "tags:cu"], **lms_config)
    has_cover = False
    cover_id_str = ""
    
    if res_status and isinstance(res_status, dict):
        playlist = res_status.get("result", {}).get("playlist_loop", [])
        if playlist and len(playlist) > 0:
            track = playlist[0]
            if track.get("artwork_url") or track.get("coverid"):
                has_cover = True
                cover_id_str = f"{track.get('coverid', '')}_{track.get('artwork_url', '')}"

    cover_path = "/tmp/lms_current_cover.jpg"
    current_cover_signature = cover_id_str if cover_id_str else state.signature

    if current_cover_signature != _last_cover_signature:
        if has_cover:
            cover_url = f'http://{lms_config["host_ip"]}:{lms_config["host_port"]}/music/current/cover.jpg?player={lms_config["player_id"]}'
            if download_cover(cover_url, cover_path):
                state.cover_path = cover_path
            else:
                state.cover_path = None
        else:
            if os.path.exists(cover_path):
                try:
                    os.remove(cover_path)
                except OSError:
                    pass
            state.cover_path = None
            
        _last_cover_signature = current_cover_signature
    else:
        state.cover_path = cover_path if has_cover and os.path.exists(cover_path) else None


class PlayerState:
    """用于在函数间传递播放器状态的简单容器"""
    def __init__(self):
        self.key = None            # 状态唯一标识 (用于屏保判断)
        self.signature = None      # 内容唯一标识 (用于刷新判断)
        self.top_text = ""
        self.bottom_text = ""
        self.album = ""            # 新增专辑字段
        self.volume = -1           # -1 表示不显示音量
        self.is_paused = False
        self.active_player_type = None # 用于记录当前占用的播放器类型
        
        # 显示参数默认值
        self.large_font = True
        self.align_mode = "center" # "center" 或 "left"
        self.is_clock = False
        
        # 进度和封面
        self.time_current = 0.0
        self.time_total = 0.0
        self.cover_path = None

def handle_airplay_state(pactl_env, source_status, last_known_volume, lms_config):
    """处理 AirPlay 状态逻辑"""
    state = PlayerState()
    state.active_player_type = "airplay"
    state.key = "airplay"
    
    # 获取 AirPlay 元数据
    artist, title, ap_vol, cover_path = update_airplay_metadata()
    
    # 判断是否暂停
    if source_status == "paused":
        # 当 AirPlay 暂停时，必须先检查 LMS 是否在播放，LMS 具有更高优先级
        error, result = get_player_status(["mode", "?"], **lms_config)
        playback_mode = extract_result_field(result, "_mode", default="stop")
        if playback_mode == "play":
            # 如果 LMS 在播放，则立即转交状态处理权
            return handle_lms_or_idle_state(pactl_env, lms_config, "squeezelite", last_known_volume)

        state.is_paused = True
        state.volume = last_known_volume
        state.top_text = "已暂停"
        state.bottom_text = title if title else "AirPlay"
        state.cover_path = cover_path
    else:
        # 优先使用 AirPlay 自身音量，如果没有则回退到系统音量
        if ap_vol >= 0: 
            state.volume = ap_vol
        else: 
            state.volume = get_system_volume(pactl_env)
            
        state.top_text = artist if artist else '未知'
        state.bottom_text = title if title else "AirPlay"
        state.cover_path = cover_path

    # 生成内容签名
    state.signature = f"ap_{artist}_{title}_{source_status}_{cover_path}"
    state.align_mode = "left"
    state.large_font = True
    return state

def handle_bluetooth_state(pactl_env, source_status, last_known_volume):
    """处理 Bluetooth 状态逻辑"""
    state = PlayerState()
    state.active_player_type = "bluetooth"
    state.key = "bluetooth"

    # 获取蓝牙元数据
    artist, title, bt_status_meta, cover_path = get_bluetooth_metadata()
    
    # 综合判定暂停状态 (PipeWire 状态 或 元数据状态)
    is_paused = (source_status == "paused") or (bt_status_meta == "paused")
    state.is_paused = is_paused

    display_title = title if title else "Bluetooth"
    display_artist = artist if artist else "未知"

    if is_paused:
        state.volume = last_known_volume
        state.top_text = "已暂停"
        state.bottom_text = display_title
    else:
        # 获取蓝牙音量
        bt_vol = get_bluetooth_volume_dbus()
        if bt_vol >= 0:
            state.volume = bt_vol
        else:
            state.volume = get_system_volume(pactl_env)
            
        state.top_text = display_artist
        state.bottom_text = display_title
    state.cover_path = cover_path

    state.signature = f"bt_{artist}_{title}_{is_paused}_{cover_path}"
    state.align_mode = "left"
    state.large_font = True
    return state

def handle_lms_or_idle_state(pactl_env, lms_config, current_active_type, last_known_volume):
    """处理 LMS (Squeezelite) 或 空闲/时钟 状态逻辑"""
    state = PlayerState()

    # 2. 查询 LMS (Squeezelite) 状态
    # 注意：这里使用 lms_config 字典解包传参
    error, result = get_player_status(
        ["mode", "?"], 
        lms_config["host_ip"], lms_config["host_port"], lms_config["player_id"]
    )
    playback_mode = extract_result_field(result, "_mode", default="stop")

    # === 场景 C1: LMS 播放中 ===
    if playback_mode == "play":
        state.active_player_type = "squeezelite"
        state.key = "squeezelite"
        
        # 获取元数据
        _, res_t = get_player_status(["current_title", "?"], **lms_config)
        _, res_a = get_player_status(["artist", "?"], **lms_config)
        _, res_al = get_player_status(["album", "?"], **lms_config)
        
        sq_title = extract_result_field(res_t, "_current_title", default="Squeezelite")
        sq_artist = extract_result_field(res_a, "_artist", default="未知")
        sq_album = extract_result_field(res_al, "_album", default="")
        
        # 获取 LMS 进度
        _, res_time = get_player_status(["time", "?"], **lms_config)
        _, res_dur = get_player_status(["duration", "?"], **lms_config)
        
        try:
            state.time_current = float(extract_result_field(res_time, "_time", default=0))
        except:
            pass
            
        try:
            state.time_total = float(extract_result_field(res_dur, "_duration", default=0))
        except:
            pass
        
        # 获取 LMS 音量
        _, vol_res = get_player_status(["mixer", "volume", "?"], **lms_config)
        lms_vol_raw = extract_result_field(vol_res, "_volume", default=None)
        try: 
            state.volume = int(float(lms_vol_raw))
        except: 
            state.volume = last_known_volume

        state.top_text = sq_artist
        state.bottom_text = sq_title
        state.album = sq_album
        state.align_mode = "left"
        state.large_font = True
        
        # 查询是否存在真实封面
        _process_lms_cover(state, lms_config)
        # 签名必须在封面处理之后生成，以包含封面路径
        state.signature = f"sq_{sq_artist}_{sq_title}_{state.cover_path}"

        return state

    # === 场景 C2: LMS 暂停 ===
    elif playback_mode == "pause" and current_active_type == "squeezelite":
        state.active_player_type = "squeezelite"
        state.key = "squeeze_pause"
        state.is_paused = True
        state.volume = last_known_volume
        
        _, res_t = get_player_status(["current_title", "?"], **lms_config)
        _, res_al = get_player_status(["album", "?"], **lms_config)
        sq_title = extract_result_field(res_t, "_current_title", default="Squeezelite")
        sq_album = extract_result_field(res_al, "_album", default="")
        
        state.top_text = "已暂停"
        state.bottom_text = sq_title
        state.album = sq_album
        state.align_mode = "left"
        state.large_font = True
        
        # 暂停时也尝试加载封面
        _process_lms_cover(state, lms_config)
        
        # 签名必须在封面处理之后生成
        state.signature = f"sq_pause_{state.cover_path}"
        
        return state

    # === 场景 C3: LMS 已停止，检查蓝牙暂停反馈 ===
    if current_active_type == "bluetooth":
        bt_artist, bt_title, bt_status_check, bt_cover_path = get_bluetooth_metadata()
        if bt_status_check == "paused":
            state.active_player_type = "bluetooth"
            state.key = "bluetooth_paused_fb"
            state.is_paused = True
            state.volume = last_known_volume
            
            state.top_text = "已暂停"
            state.bottom_text = bt_title if bt_title else "Bluetooth"
            state.align_mode = "left"
            state.signature = f"bt_paused_fb_{bt_cover_path}"
            state.cover_path = bt_cover_path
            state.large_font = True
            return state
            
    
    if check_bluetooth_connected(pactl_env):
        # 蓝牙已连接但未播放
        state.key = "bt_connected"
        state.top_text = "Bluetooth"
        state.bottom_text = "已连接"
        state.signature = "bt_conn"
        state.large_font = True
        state.active_player_type = "bluetooth" # 标记为蓝牙，即使未播放
    else:
        # 时钟模式
        state.key = "idle"
        state.is_clock = True
        state.top_text = time.strftime("%Y-%m-%d", time.localtime())
        state.bottom_text = time.strftime("%H:%M:%S", time.localtime())
        state.signature = "idle"
        state.large_font = True
        state.active_player_type = None # 纯空闲，无活跃播放器
        
    state.volume = -1 # 不显示音量
    return state
