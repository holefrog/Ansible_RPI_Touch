#!/usr/bin/env python
# resources/ts/config.py - 修复版：支持日志级别配置

import configparser
import os
import logging
from ui_config_parser import load_ui_config

# 动态获取当前脚本所在的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "ts.ini")

def load_config():
    """
    加载完整配置文件
    
    Returns:
        dict: 包含所有配置的字典
        {
            "lms": (host_ip, host_port, player_id),
            "ts": (bus, address, width, height, log_level),
            "display": {...},
            "screensaver": {...},
            "volume": {...},
            "airplay": {...},
            "ui": {...}  # 从 ui_config.toml 加载的配置
        }
    """
    
    # 检查配置文件是否存在
    if not os.path.exists(CONFIG_FILE):
        logging.error(f"错误：未找到配置文件 {CONFIG_FILE}")
        logging.error("请创建配置文件并填写必要信息")
        exit(1)
    
    config = configparser.ConfigParser()
    
    try:
        config.read(CONFIG_FILE)
    except Exception as e:
        logging.error(f"配置文件读取失败: {e}")
        exit(1)
    
    try:
        # ============================================
        # 1. LMS 服务器配置
        # ============================================
        host_ip = config.get("SERVER", "HOST_IP")
        host_port = config.get("SERVER", "HOST_Port")
        player_id = config.get("SERVER", "PLAYER_ID")
            
        # ============================================
        # 2. Touchscreen 硬件配置
        # ============================================
        ts_width = config.getint("TS", "width", fallback=480)
        ts_height = config.getint("TS", "height", fallback=320)
        
        # SPI (Display)
        ts_spi_bus = config.getint("TS", "spi_bus", fallback=0)
        ts_spi_device = config.getint("TS", "spi_device", fallback=0)
        ts_spi_speed_hz = config.getint("TS", "spi_speed_hz", fallback=20000000)
        ts_dc_pin = config.getint("TS", "dc_pin", fallback=25)
        ts_rst_pin = config.getint("TS", "rst_pin", fallback=27)
        ts_bl_pin = config.getint("TS", "bl_pin", fallback=13)
        
        # I2C (Touch)
        ts_i2c_bus = config.getint("TS", "i2c_bus", fallback=3)
        ts_i2c_address_str = config.get("TS", "i2c_address", fallback="0x38")
        ts_tp_rst_pin = config.getint("TS", "tp_rst_pin", fallback=17)
        
        # 🆕 读取日志级别配置
        log_level_str = config.get("TS", "log_level", fallback="INFO").upper()
        
        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level_str not in valid_levels:
            logging.warning(f"无效的日志级别: {log_level_str}，使用默认值 INFO")
            log_level_str = "INFO"
        
        # 转换为 logging 常量
        log_level = getattr(logging, log_level_str)
        
        # 将地址字符串转换为整数
        ts_i2c_address = int(ts_i2c_address_str, 16)
        
        # ============================================
        # 3. 显示配置
        # ============================================
        default_brightness = config.getint("DISPLAY", "default_brightness", fallback=255)
        dim_brightness = config.getint("DISPLAY", "dim_brightness", fallback=8)
        media_dim_brightness = config.getint("DISPLAY", "media_dim_brightness", fallback=32)
        marquee_speed = config.getint("DISPLAY", "marquee_speed", fallback=50)
        
        # ============================================
        # 4. 屏保配置
        # ============================================
        # 屏保及息屏超时属于系统硬件与电源管理行为，统一定义在 ts.ini 中最为合理
        idle_dim_timeout = config.getint("SCREENSAVER", "idle_dim_timeout", fallback=10)
        media_dim_timeout = config.getint("SCREENSAVER", "media_dim_timeout", fallback=60)
        off_timeout = config.getint("SCREENSAVER", "off_timeout", fallback=900)
        
        # ============================================
        # 5. 弹窗配置 (POPUP)
        # ============================================
        popup_duration = config.getfloat("POPUP", "popup_duration", fallback=3.0)
        
        # ============================================
        # 6. AirPlay 配置
        # ============================================
        metadata_pipe = config.get("AIRPLAY", "metadata_pipe", fallback="/tmp/shairport-sync-metadata")
        
        # ============================================
        # 日志输出
        # ============================================
        logging.info("=" * 50)
        logging.info("配置加载成功")
        logging.info("=" * 50)
        logging.info(f"LMS 服务器: {host_ip}:{host_port}")
        logging.info(f"播放器 ID: {player_id}")
        logging.info(f"TS: SPI bus={ts_spi_bus}, speed={ts_spi_speed_hz}, I2C bus={ts_i2c_bus}, addr=0x{ts_i2c_address:X}, size={ts_width}x{ts_height}")
        logging.info(f"日志级别: {log_level_str}")
        logging.info(f"显示: 默认={default_brightness}, 待机暗={dim_brightness}, 播放暗={media_dim_brightness}, 滚动={marquee_speed}")
        logging.info(f"屏保: 待机暗={idle_dim_timeout}s, 播放暗={media_dim_timeout}s, 关={off_timeout}s")
        logging.info(f"弹窗超时: {popup_duration}s")
        logging.info(f"AirPlay 管道: {metadata_pipe}")
        logging.info("=" * 50)
        
        # ============================================
        # 7. UI 新架构配置 (ui_config.toml)
        # ============================================
        ui_config = load_ui_config()

        # ============================================
        # 返回配置字典
        # ============================================
        return {
            "lms": {
                "host_ip": host_ip,
                "host_port": host_port,
                "player_id": player_id,
            },
            "ts": {
                "width": ts_width,
                "height": ts_height,
                "spi_bus": ts_spi_bus,
                "spi_device": ts_spi_device,
                "spi_speed_hz": ts_spi_speed_hz,
                "dc_pin": ts_dc_pin,
                "rst_pin": ts_rst_pin,
                "bl_pin": ts_bl_pin,
                "i2c_bus": ts_i2c_bus,
                "i2c_address": ts_i2c_address,
                "tp_rst_pin": ts_tp_rst_pin,
                "log_level": log_level,
            },
            "display": {
                "default_brightness": default_brightness,
                "dim_brightness": dim_brightness,
                "media_dim_brightness": media_dim_brightness,
                "marquee_speed": marquee_speed,
            },
            "screensaver": {
                "idle_dim_timeout": idle_dim_timeout,
                "media_dim_timeout": media_dim_timeout,
                "off_timeout": off_timeout,
            },
            "popup": {
                "duration": popup_duration,
            },
            "airplay": {
                "metadata_pipe": metadata_pipe,
            },
            "ui": ui_config
        }
        
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logging.error(f"配置文件格式无效: {e}")
        logging.error("请确保 ts.ini 包含所有必需的 section")
        exit(1)

# 测试代码
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n=== 配置加载测试 ===\n")
    cfg = load_config()
    
    print(f"LMS 配置: {cfg['lms']}")
    print(f"TS 配置: {cfg['ts']}")
    print(f"显示配置: {cfg['display']}")
    print(f"屏保配置: {cfg['screensaver']}")
    print(f"弹窗配置: {cfg['popup']}")
    print(f"AirPlay 配置: {cfg['airplay']}")
