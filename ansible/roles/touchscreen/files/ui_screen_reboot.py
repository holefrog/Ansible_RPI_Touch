from PIL import Image, ImageDraw
import logging
from ui_core import BaseUIRenderer

logger = logging.getLogger("RebootScreen")

class RebootScreenRenderer(BaseUIRenderer):
    """
    系统重启提示屏幕
    显示纯黑底色或配置的颜色，及提示文字，防止 UI 假死
    """
    def __init__(self, display_ctx, ui_cfg):
        super().__init__(display_ctx)
        self.cfg = ui_cfg.get("screens", {}).get("reboot", {})
        self.bg_color = self.hex_to_rgb(self.cfg.get("bg_color", "#000000"))

    def render(self):
        """生成重启屏幕画面"""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        # Title
        title_cfg = self.cfg.get("title", {})
        text = title_cfg.get("text", "System Rebooting...")
        font_size = title_cfg.get("font_size", 24)
        color = self.hex_to_rgb(title_cfg.get("color", "#E74C3C"))
        
        font = self.get_font(font_size)
        
        # Calculate text size for centering
        try:
            bbox = font.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(text, font=font)
            
        x = (self.width - tw) // 2
        y = (self.height - th) // 2
        
        draw.text((x, y), text, font=font, fill=color)
        return img
