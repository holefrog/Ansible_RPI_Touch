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

logger = logging.getLogger(__name__)
# ============================================
# System & Service Info
# ============================================
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read()) / 1000.0
    except:
        return 0.0

def get_cpu_usage():
    try:
        out = subprocess.check_output("top -bn1 | grep -i '%Cpu(s)'", shell=True, text=True)
        m = re.search(r'(\d+\.\d+)\s+id', out)
        if m:
            idle = float(m.group(1))
            return 100.0 - idle
    except:
        pass
    return 0.0

def get_mem_usage():
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        mem_total = 0
        mem_available = 0
        for line in lines:
            if line.startswith('MemTotal:'):
                mem_total = int(line.split()[1])
            elif line.startswith('MemAvailable:'):
                mem_available = int(line.split()[1])
        if mem_total > 0:
            mem_used = mem_total - mem_available
            return mem_total * 1024, mem_used * 1024 # return bytes
    except Exception:
        pass
    return 0, 0

def get_disk_usage(path='/'):
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        return total, used
    except Exception:
        return 0, 0

def get_ip_address(ifname):
    import fcntl
    import struct
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
    except Exception:
        return "N/A"

def get_wifi_quality():
    try:
        with open("/proc/net/wireless", "r") as f:
            lines = f.readlines()
        for line in lines[2:]:
            data = line.split()
            if len(data) >= 3:
                # Link quality is in the 3rd column, stripping the dot
                quality = int(data[2].strip('.'))
                return True, quality
    except Exception:
        pass
    return False, 0

def get_system_info():
    wifi_connected, wifi_quality = get_wifi_quality()
    info = {
        "cpu_temp": get_cpu_temp(),
        "cpu_usage": get_cpu_usage(),
        "eth0_ip": get_ip_address('eth0'),
        "wlan0_ip": get_ip_address('wlan0'),
        "wifi_connected": wifi_connected,
        "wifi_quality": wifi_quality
    }
    
    rt, ru = get_mem_usage()
    info["ram_total"] = rt
    info["ram_used"] = ru
    
    dt, du = get_disk_usage()
    info["disk_total"] = dt
    info["disk_used"] = du
    
    return info

def get_services_status():
    uid = os.getuid()
    env = os.environ.copy()
    if "XDG_RUNTIME_DIR" not in env:
        env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
    if "DBUS_SESSION_BUS_ADDRESS" not in env:
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"

    services = {
        "squeezelite": ("user", "squeezelite"),
        "shairport-sync": ("user", "shairport-sync"),
        "bluetooth": ("system", "bluetooth"),
        "bluetooth-a2dp-autopair": ("system", "bluetooth-a2dp-autopair"),
        "pipewire": ("user", "pipewire"),
        "wireplumber": ("user", "wireplumber"),
        "volume": ("user", "volume")
    }
    
    status = {}
    for key, (mode, name) in services.items():
        try:
            cmd = ["systemctl", "is-active", name]
            if mode == "user":
                cmd.insert(1, "--user")
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3, env=env)
                if res.stdout.strip() != "active":
                    cmd_sys = ["systemctl", "is-active", name]
                    res_sys = subprocess.run(cmd_sys, capture_output=True, text=True, timeout=3)
                    status[key] = (res_sys.stdout.strip() == "active")
                else:
                    status[key] = True
            else:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                status[key] = (res.stdout.strip() == "active")
        except Exception as e:
            logger.error(f"Error checking {name}: {e}")
            status[key] = False
            
    return status
