import os
import logging
from PIL import Image, ImageDraw
from ui_core import BaseUIRenderer

class PhotoScreenRenderer(BaseUIRenderer):
    def __init__(self, display_ctx, ui_config):
        super().__init__(display_ctx, ui_config)
        self.cached_cover_key = None
        self.cached_img = None
        self.logger = logging.getLogger("PhotoUI")

    def render(self, player_state):
        # 使用与主界面相同的缓存验证逻辑，避免重复耗时计算
        cover_path = getattr(player_state, "cover_path", None)
        if not cover_path or not os.path.exists(cover_path):
            cover_path = self.default_cover_path
            
        try:
            cover_mtime = os.path.getmtime(cover_path)
        except OSError:
            cover_mtime = 0
            
        current_cover_key = (cover_path, cover_mtime)

        # 只有在封面变更或缓存丢失时才重新生成相框画面
        if self.cached_cover_key != current_cover_key or self.cached_img is None:
            img = Image.new("RGB", (self.width, self.height), "black")
            try:
                bg_img = Image.open(cover_path).convert("RGB")
                img_w, img_h = bg_img.size
                
                # Contain 模式：保持比例，完整显示封面
                ratio = min(self.width / img_w, self.height / img_h)
                new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                bg_img = bg_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                offset_x = (self.width - new_w) // 2
                offset_y = (self.height - new_h) // 2
                img.paste(bg_img, (offset_x, offset_y))
            except Exception as e:
                self.logger.error(f"无法加载照片 {cover_path}: {e}")
                
            self.cached_img = img
            self.cached_cover_key = current_cover_key
            
        return self.cached_img.copy()