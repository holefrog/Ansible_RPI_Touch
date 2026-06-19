#!/usr/bin/env python
# ui_screen_mask.py
# v2

import time
from PIL import Image, ImageDraw, ImageFont
from ui_core import BaseUIRenderer
import math

class MaskScreenRenderer(BaseUIRenderer):
    def render(self, base_img, player_state, active_button=None):
        """渲染蒙板界面
        
        Args:
            base_img: 底层主屏图像
            player_state: 当前播放状态
            active_button: 被点击的按键名 ("prev" / "play_pause" / "next" / None)
                          非 None 时在对应热区绘制高亮背景
        """
        mask_cfg = self.config.get("screens", {}).get("mask", {})
        
        # 1. 创建半透明遮罩
        opacity = mask_cfg.get("opacity", 0.85)
        bg_color_hex = mask_cfg.get("bg_color", "#121212")
        r, g, b = self.hex_to_rgb(bg_color_hex)
        
        overlay = Image.new("RGBA", (self.width, self.height), (r, g, b, int(255 * opacity)))
        draw = ImageDraw.Draw(overlay)

        # 2. 热区定义（与 main.py 触摸判断坐标保持一致）
        # 除去顶部状态栏，其它屏幕水平均分三份
        section_w = self.width // 3
        status_bar_height = self.config.get("screens", {}).get("status_top", {}).get("height", 60)
        y_min = status_bar_height
        y_max = self.height

        # button_name -> (x1, y1, x2, y2)
        hit_zones = {
            "prev":       (0, y_min, section_w, y_max),
            "play_pause": (section_w, y_min, section_w * 2, y_max),
            "next":       (section_w * 2, y_min, self.width, y_max),
        }

        # 4. 绘制控制按钮图标
        icon_map = {
            "skip_previous": "\ue045",
            "pause":         "\ue034",
            "play":          "\ue037",
            "skip_next":     "\ue044",
        }

        def draw_icon(cfg, default_icon, default_pos, btn_name):
            pos  = cfg.get("pos", default_pos)
            size = cfg.get("font_size", 44)

            # 激活按键图标变色，并在对应热区绘制高亮背景
            if active_button == btn_name:
                color = (29, 185, 84, 255)
                hz = hit_zones.get(btn_name)
                if hz:
                    # 绘制半透明圆角矩形作为热区点击反馈
                    draw.rounded_rectangle(hz, radius=16, fill=(255, 255, 255, 25))
            else:
                color = self.hex_to_rgb(cfg.get("color", "#FFFFFF")) + (255,)

            icon_name = cfg.get("icon", default_icon)

            # 播放/暂停按键根据当前状态切换图标
            if default_icon in ["play", "pause"]:
                is_paused = getattr(player_state, "is_paused", False)
                icon_name = "play" if is_paused else "pause"

            icon_char = icon_map.get(icon_name, "?")

            try:
                font = self.get_icon_font(size)
            except IOError:
                font = ImageFont.load_default()

            draw.text(tuple(pos), icon_char, font=font, fill=color)

        prev_cfg       = mask_cfg.get("prev_btn", {})
        play_pause_cfg = mask_cfg.get("play_pause_btn", {})
        next_cfg       = mask_cfg.get("next_btn", {})

        draw_icon(prev_cfg,       "skip_previous", [90,  135], "prev")
        draw_icon(play_pause_cfg, "pause",         [222, 135], "play_pause")
        draw_icon(next_cfg,       "skip_next",     [350, 135], "next")

        # 5. 超时提示文本
        timeout_cfg   = mask_cfg.get("timeout_label", {})
        timeout_font  = self.get_font(timeout_cfg.get("font_size", 14))
        timeout_color = self.hex_to_rgb(timeout_cfg.get("color", "#555D6B"))
        timeout_text  = timeout_cfg.get("text", "稍后自动关闭")
        
        # 动态计算居中 X 坐标
        if hasattr(draw, "textlength"):
            timeout_w = draw.textlength(timeout_text, font=timeout_font)
        else:
            timeout_w = draw.textsize(timeout_text, font=timeout_font)[0]
        timeout_pos = ((self.width - timeout_w) // 2, timeout_cfg.get("pos", [190, 288])[1])
        draw.text(timeout_pos, timeout_text, font=timeout_font, fill=timeout_color + (255,))

        # 合成到底图
        final_img = base_img.convert("RGBA")
        final_img.alpha_composite(overlay)
        return final_img.convert("RGB")
