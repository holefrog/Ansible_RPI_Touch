#!/usr/bin/env python
# resources/ts/query.py (重构版 - 修复审核建议 #6)
import base64
import getpass
import json
import logging
import os
import re
import socket
import subprocess
import time

import requests

try:
    import pydbus
    PYDBUS_AVAILABLE = True
except ImportError:
    PYDBUS_AVAILABLE = False

logger = logging.getLogger(__name__)


BT_VOLUME_MAX = 127  # Bluetooth A2DP volume range: 0-127

# ============================================
# 全局状态
# ============================================
_AIRPLAY_PIPE = None
_airplay_state = {"artist": "", "title": "", "volume": -1, "buffer": "", "cover_path": None, "cover_time": 0}
_pipe_fd = None
_bt_player_path = None
_last_bt_volume = -1


# ============================================
# AirPlay 管道初始化（修复审核建议 #6 - 强制初始化）
# ============================================
def init_airplay_pipe(pipe_path):
    """
    初始化 AirPlay metadata 管道路径（必须在使用前调用）

    Args:
        pipe_path: 从配置文件读取的管道路径
        
    Raises:
        RuntimeError: 如果管道路径无效
    """
    global _AIRPLAY_PIPE
    
    if not pipe_path:
        raise RuntimeError("AirPlay 管道路径不能为空")
    
    _AIRPLAY_PIPE = pipe_path
    logger.info(f"AirPlay 管道路径已设置: {_AIRPLAY_PIPE}")


# ============================================
# 基础网络/LMS
# ============================================
def check_network(host, port):
    try:
        socket.create_connection((host, port), timeout=5)
        return True
    except socket.error as e:
        logger.error(f"Network check failed: {host}:{port}, error={e}")
        return False


def get_player_status(cmd, host_ip, host_port, player_id, retries=3, delay=2):
    url = f'http://{host_ip}:{host_port}/jsonrpc.js'
    headers = {'Content-Type': 'application/json'}
    data = {"id": 1, "method": "slim.request", "params": [player_id, cmd]}

    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=1)
            response.raise_for_status()
            return None, response.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.2)
            else:
                return f"Error: {e}", None


def extract_result_field(result, field, default="N/A"):
    if not isinstance(result, dict):
        return default
    result_dict = result.get('result', {})
    if not isinstance(result_dict, dict):
        return default
    return result_dict.get(field, default)

def download_cover(url, save_path):
    """下载封面，并利用 HTTP If-Modified-Since 头部避免不必要的下载"""
    headers = {}
    # 如果文件已存在，则添加 If-Modified-Since 头
    if os.path.exists(save_path):
        try:
            mtime = os.path.getmtime(save_path)
            # 格式化为 HTTP-Date
            headers['If-Modified-Since'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mtime))
        except OSError:
            pass # 文件存在但无法获取时间，忽略

    try:
        response = requests.get(url, timeout=2, headers=headers)
        # 如果服务器返回 304 Not Modified，说明本地缓存仍然有效
        if response.status_code == 304:
            return True
        # 如果服务器返回 200 OK，则下载新内容
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True # 下载成功
    except Exception as e:
        logger.warning(f"Failed to download cover art: {e}")
    return False


# ============================================
# PipeWire 状态
# ============================================
def setup_pactl_env():
    user = getpass.getuser()
    uid = os.getuid()
    env = os.environ.copy()
    if "XDG_RUNTIME_DIR" not in env:
        env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
    env["LC_ALL"] = "C"
    return env


def get_high_priority_source(pactl_env):
    """
    检查 PipeWire 活跃源
    Returns: (source_type, status)
             status: "playing" | "paused"
    """
    try:
        env = pactl_env.copy()
        env["LC_ALL"] = "C"

        result = subprocess.run(
            ['pactl', 'list', 'sink-inputs'],
            capture_output=True,
            text=True,
            check=True,
            env=env,
            timeout=1
        )
        output = result.stdout.lower()
        sink_inputs = output.split('sink input #')

        # 第一轮：查找正在播放的
        for block in sink_inputs:
            if not block.strip():
                continue
            if "corked: no" in block:
                if "shairport" in block:
                    return "airplay", "playing"
                if "bluez" in block:
                    return "bluetooth", "playing"

        # 第二轮：查找已暂停的
        for block in sink_inputs:
            if not block.strip():
                continue
            if "corked: yes" in block:
                if "shairport" in block:
                    return "airplay", "paused"
                if "bluez" in block:
                    return "bluetooth", "paused"

    except Exception as e:
        logger.warning(f"Pactl check failed: {e}")

    return None, "stopped"


def check_bluetooth_connected(pactl_env):
    try:
        result = subprocess.run(
            ["pactl", "list", "sinks"],
            capture_output=True,
            text=True,
            check=True,
            env=pactl_env,
            timeout=1,
        )
        return "bluez_sink" in result.stdout.lower()
    except Exception:
        return False


def get_system_volume(pactl_env):
    try:
        result = subprocess.run(
            ['pactl', 'get-sink-volume', '@DEFAULT_SINK@'],
            capture_output=True,
            text=True,
            check=True,
            env=pactl_env,
            timeout=1
        )
        m = re.search(r'(\d+)%', result.stdout)
        if m:
            return max(0, min(100, int(m.group(1))))
    except Exception:
        pass
    return 0


# ============================================
# AirPlay 元数据（修复审核建议 #6 - 强制检查）
# ============================================
def update_airplay_metadata():
    """
    读取 AirPlay metadata 管道

    Returns:
        tuple: (artist, title, volume)
        
    Raises:
        RuntimeError: 如果管道路径未初始化
    """
    global _pipe_fd, _airplay_state, _AIRPLAY_PIPE

    # 修复审核建议 #6：强制中断而非仅记录错误
    if _AIRPLAY_PIPE is None:
        raise RuntimeError(
            "AirPlay 管道路径未初始化！必须先调用 init_airplay_pipe()\n"
            "请检查 main.py 是否正确调用了初始化函数。"
        )

    if _pipe_fd is None:
        if os.path.exists(_AIRPLAY_PIPE):
            try:
                _pipe_fd = os.open(_AIRPLAY_PIPE, os.O_RDONLY | os.O_NONBLOCK)
                logger.info(f"Pipe opened: {_AIRPLAY_PIPE}")
            except Exception as e:
                logger.error(f"Failed to open pipe: {e}")
        return _airplay_state["artist"], _airplay_state["title"], _airplay_state["volume"], _airplay_state.get("cover_path")

    try:
        while True:
            chunk = os.read(_pipe_fd, 8192)
            if not chunk:
                break
            _airplay_state["buffer"] += chunk.decode('utf-8', errors='ignore')
    except BlockingIOError:
        pass
    except Exception:
        try:
            os.close(_pipe_fd)
        except Exception:
            pass
        _pipe_fd = None
        return _airplay_state["artist"], _airplay_state["title"], _airplay_state["volume"], _airplay_state.get("cover_path")

    while '<item>' in _airplay_state["buffer"] and '</item>' in _airplay_state["buffer"]:
        start = _airplay_state["buffer"].find('<item>')
        end = _airplay_state["buffer"].find('</item>') + 7
        item_block = _airplay_state["buffer"][start:end]
        _airplay_state["buffer"] = _airplay_state["buffer"][end:]

        try:
            code_match = re.search(r'<code>([0-9a-f]+)</code>', item_block)
            if not code_match:
                continue
            code = code_match.group(1)
            data_match = re.search(
                r'<data encoding="base64">\s*([A-Za-z0-9+/=\s]+)\s*</data>',
                item_block,
                re.DOTALL
            )
            if not data_match:
                continue
            base64_str = re.sub(r'\s+', '', data_match.group(1))

            if code == '6d696e6d':  # minm (Title)
                new_title = base64.b64decode(base64_str).decode('utf-8', errors='ignore')
                # 发现歌名发生变化，且距离上次收到封面超过2秒，则清空上一首歌的缓存封面
                if _airplay_state.get("title") != new_title:
                    if time.time() - _airplay_state.get("cover_time", 0) > 2.0:
                        _airplay_state["cover_path"] = None
                _airplay_state["title"] = new_title
            elif code == '61736172':  # asar (Artist)
                _airplay_state["artist"] = base64.b64decode(base64_str).decode('utf-8', errors='ignore')
            elif code == '70766f6c':  # pvol (Volume)
                try:
                    vol_str = base64.b64decode(base64_str).decode('utf-8', errors='ignore')
                    parts = vol_str.split(',')
                    if len(parts) >= 1:
                        curr_db = float(parts[0])
                        min_db = -30.0
                        max_db = 0.0
                        if len(parts) >= 4:
                            max_db = float(parts[3])
                        
                        new_vol = 0
                        if curr_db < -100:
                            new_vol = 0
                        elif curr_db >= max_db:
                            new_vol = 100
                        elif curr_db <= min_db:
                            new_vol = 0
                        else:
                            pct = (curr_db - min_db) / (max_db - min_db) * 100
                            new_vol = int(max(0, min(100, pct)))
                        _airplay_state["volume"] = new_vol
                except Exception:
                    pass
            elif code == '50494354':  # PICT (Picture / Cover Art)
                try:
                    img_data = base64.b64decode(base64_str)
                    cover_path = "/tmp/airplay_cover.jpg"
                    with open(cover_path, "wb") as f:
                        f.write(img_data)
                    _airplay_state["cover_path"] = cover_path
                    _airplay_state["cover_time"] = time.time()
                except Exception as e:
                    logger.warning(f"Failed to save AirPlay cover: {e}")
        except Exception:
            pass

    return _airplay_state["artist"], _airplay_state["title"], _airplay_state["volume"], _airplay_state.get("cover_path")


# ============================================
# Bluetooth
# ============================================
def get_bluetooth_volume_dbus():
    global _last_bt_volume
    try:
        cmd = [
            "dbus-send",
            "--system",
            "--dest=org.bluez",
            "--print-reply",
            "/",
            "org.freedesktop.DBus.ObjectManager.GetManagedObjects"
        ]
        output = subprocess.check_output(cmd, timeout=1).decode()
        paths = re.findall(r'object path "(/org/bluez/hci[0-9]*/dev_[^"]+)"', output)
        
        for path in paths:
            if "/fd" not in path:
                continue
            try:
                cmd_vol = [
                    "dbus-send",
                    "--system",
                    "--print-reply",
                    "--dest=org.bluez",
                    path,
                    "org.freedesktop.DBus.Properties.Get",
                    "string:org.bluez.MediaTransport1",
                    "string:Volume",
                ]
                res = subprocess.check_output(
                    cmd_vol,
                    stderr=subprocess.DEVNULL,
                    timeout=0.5
                ).decode()
                m = re.search(r'uint16\s+(\d+)', res)
                if m:
                    return int((int(m.group(1)) / BT_VOLUME_MAX) * 100)
            except Exception:
                continue
    except Exception:
        pass
    return -1


def get_bluetooth_metadata():
    """获取蓝牙信息，返回: (Artist, Title, Status)"""
    if not PYDBUS_AVAILABLE:
        return "", "", "unknown", None

    try:
        bus = pydbus.SystemBus()
        manager = bus.get('org.bluez', '/')
        managed_objects = manager.GetManagedObjects()

        for path, interfaces in managed_objects.items():
            if 'org.bluez.MediaPlayer1' in interfaces:
                player = interfaces['org.bluez.MediaPlayer1']
                
                track_info = player.get('Track', {})
                artist = track_info.get('Artist', '')
                title = track_info.get('Title', '')
                cover_path = track_info.get('AlbumArt') # Might be None
                
                status = player.get('Status', 'unknown').lower()

                return artist, title, status, cover_path

    except Exception as e:
        # This can happen if bluetooth service is down or no player is available
        # logger.debug(f"Failed to get bluetooth metadata via pydbus: {e}")
        pass
        
    return "", "", "unknown", None

def get_bluetooth_volume_dbus():
    """使用 pydbus 高效获取蓝牙设备音量"""
    if not PYDBUS_AVAILABLE:
        return -1

    try:
        bus = pydbus.SystemBus()
        manager = bus.get('org.bluez', '/')
        managed_objects = manager.GetManagedObjects()

        for path, interfaces in managed_objects.items():
            if 'org.bluez.MediaTransport1' in interfaces:
                transport = interfaces['org.bluez.MediaTransport1']
                volume = transport.get('Volume') # This is a uint16
                if volume is not None:
                    # 将 0-127 的音量范围转换为 0-100 的百分比
                    return int((volume / BT_VOLUME_MAX) * 100)
    except Exception as e:
        # logger.debug(f"Failed to get bluetooth volume via pydbus: {e}")
        pass
        
    return -1
