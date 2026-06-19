#!/usr/bin/env python
# ui_volume_popup.py
# v1

from PIL import Image, ImageDraw
from ui_core import BaseUIRenderer


class VolumePopupRenderer(BaseUIRenderer):
    """
    在主屏底部居中叠加一个音量弹窗。
    点击弹窗内滑条区域调节音量；点击弹窗外区域关闭弹窗。

    弹窗几何（与 main.py 触摸判断保持一致）：
        popup_w = 320, popup_h = 48, margin_bottom = 20
        px = (screen_w - popup_w) // 2
        py = screen_h - popup_h - margin_bottom
        bar_x = px + 46
        bar_w = popup_w - 46 - 40
    """

    POPUP_W        = 320
    POPUP_H        = 48
    MARGIN_BOTTOM  = 20
    ICON_AREA_W    = 46   # 喇叭图标占用宽度（含左 padding）
    PCT_AREA_W     = 40   # 百分比文字占用宽度（含右 padding）

    def render(self, base_img, volume):
        """
        Args:
            base_img: 底层主屏图像（RGB）
            volume:   当前音量 0-100

        Returns:
            合成后的 RGB 图像
        """
        pw = self.POPUP_W
        ph = self.POPUP_H
        mb = self.MARGIN_BOTTOM

        px = (self.width  - pw) // 2
        py = self.height - ph - mb

        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        # 背景圆角矩形
        draw.rounded_rectangle(
            (px, py, px + pw, py + ph),
            radius=12,
            fill=(30, 30, 30, 220),
        )

        # 喇叭图标
        try:
            icon_font = self.get_icon_font(20)
            vol_icon  = "\ue050" if volume > 0 else "\ue04f" # Material Icons: volume_up / volume_off
            draw.text((px + 14, py + 14), vol_icon, font=icon_font, fill=(200, 200, 200, 255))
        except Exception:
            pass  # 图标字体缺失时跳过，不影响滑条

        # 滑条轨道
        bar_x = px + self.ICON_AREA_W
        bar_w = pw - self.ICON_AREA_W - self.PCT_AREA_W
        bar_cy = py + ph // 2          # 滑条垂直中心
        bar_h  = 4

        draw.rounded_rectangle(
            (bar_x, bar_cy - bar_h // 2, bar_x + bar_w, bar_cy + bar_h // 2),
            radius=2,
            fill=(80, 80, 80, 255),
        )

        # 滑条填充
        vol      = max(0, min(100, volume))
        fill_w   = int(bar_w * vol / 100)
        if fill_w > 0:
            draw.rounded_rectangle(
                (bar_x, bar_cy - bar_h // 2, bar_x + fill_w, bar_cy + bar_h // 2),
                radius=2,
                fill=(255, 255, 255, 255),
            )

        # 滑块圆点
        knob_x = bar_x + fill_w
        knob_r = 7
        draw.ellipse(
            (knob_x - knob_r, bar_cy - knob_r, knob_x + knob_r, bar_cy + knob_r),
            fill=(255, 255, 255, 255),
        )

        # 百分比文字
        pct_font = self.get_font(14)
        pct_text = f"{vol}%"
        pct_x    = px + pw - self.PCT_AREA_W + 4
        pct_y    = py + (ph - 14) // 2
        draw.text((pct_x, pct_y), pct_text, font=pct_font, fill=(200, 200, 200, 255))

        result = base_img.convert("RGBA")
        result.alpha_composite(overlay)
        return result.convert("RGB")
