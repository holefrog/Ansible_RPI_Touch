#!/usr/bin/env python
# resources/ts/display.py

import logging
import os
import time
from st7796 import st7796


# ============================================
# 日志配置 (统一格式)
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Display")

# -------------------------------
# 屏幕 初始化
# -------------------------------
def init_display(ts_config: dict, display_config: dict):
    """
    初始化屏幕显示设备
    
    Args:
        ts_config: 触摸屏硬件配置字典
        display_config: 显示配置字典（包含字体、亮度等）
    """
    try:
        w = ts_config["width"]
        h = ts_config["height"]
        
        logger.info("初始化 SPI 屏幕 (使用厂商 st7796 驱动)")
        device = st7796(
            spi_bus=ts_config["spi_bus"],
            spi_device=ts_config["spi_device"],
            spi_freq=ts_config["spi_speed_hz"],
            rst_pin=ts_config["rst_pin"],
            dc_pin=ts_config["dc_pin"],
            bl_pin=ts_config["bl_pin"]
        )
        
        # st7796 驱动内部已初始化，直接获取引用
        backlight = device.GPIO_BL_PIN
        
        # 从配置读取亮度
        default_brightness = display_config.get("default_brightness", 255)
        dim_brightness = display_config.get("dim_brightness", 8)
        media_dim_brightness = display_config.get("media_dim_brightness", 32)
        marquee_speed = display_config.get("marquee_speed", 50)
        
        logger.info("Display 配置已加载:")
        for key, value in display_config.items():
            logger.info(f"  {key} = {value}")
        
        return {
            "device": device, 
            "width": w, 
            "height": h,
            "backlight": backlight,
            "default_brightness": default_brightness, 
            "dim_brightness": dim_brightness,
            "media_dim_brightness": media_dim_brightness,
            "marquee_speed": marquee_speed,
        }
    except Exception as e:
        logger.error(f"屏幕初始化失败: {e}")
        raise

def set_brightness(display_ctx: dict, level: int):
    # 映射 0-255 的亮度级别到 gpiozero 要求的 0.0-1.0 占空比
    val = max(0.0, min(1.0, level / 255.0))
    current_val = display_ctx["backlight"].value
    
    # 柔和淡出 (Fade-out) 效果，用于变暗过渡
    if current_val > val:
        steps = 20
        step_val = (current_val - val) / steps
        for _ in range(steps):
            current_val -= step_val
            display_ctx["backlight"].value = max(val, current_val)
            time.sleep(0.015)
            
    display_ctx["backlight"].value = val

def restore_brightness(display_ctx: dict):
    target = display_ctx["default_brightness"]
    target_val = max(0.0, min(1.0, target / 255.0))
    current_val = display_ctx["backlight"].value
    
    # 柔和淡入 (Fade-in) 效果
    if current_val < target_val:
        steps = 20
        step_val = (target_val - current_val) / steps
        for _ in range(steps):
            current_val += step_val
            display_ctx["backlight"].value = min(target_val, current_val)
            time.sleep(0.015)  # 总耗时约 0.3 秒，平滑舒适过渡
            
    display_ctx["backlight"].value = target_val

def turn_off_display(display_ctx: dict):
    current_val = display_ctx["backlight"].value
    
    # 彻底熄屏前淡出
    if current_val > 0.0:
        steps = 20
        step_val = current_val / steps
        for _ in range(steps):
            current_val -= step_val
            display_ctx["backlight"].value = max(0.0, current_val)
            time.sleep(0.015)
            
    display_ctx["backlight"].value = 0.0

def turn_on_display(display_ctx: dict):
    try:
        # 强制唤醒 LCD 控制器显示，防止深休眠导致背光亮但无内容
        display_ctx["device"].command(0x29)
    except Exception:
        pass
    restore_brightness(display_ctx)
