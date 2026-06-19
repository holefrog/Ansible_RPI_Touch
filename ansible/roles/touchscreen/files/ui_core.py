import os
import logging
from PIL import ImageFont

logger = logging.getLogger("UICore")

STATUS_FONT = ImageFont.load_default()

# 模块级全局字体缓存，确保整个应用生命周期内同一字号仅被加载一次
_FONT_CACHE = {}
_ICON_FONT_CACHE = {}
_CLOCK_FONT_CACHE = {}

class BaseUIRenderer:
    def __init__(self, display_ctx, ui_config):
        self.ctx = display_ctx
        self.config = ui_config
        self.device = display_ctx["device"]
        self.width = display_ctx["width"]
        self.height = display_ctx["height"]
        
        global_cfg = self.config.get("global", {})
        
        # [单点配置原则] 
        # 此处的第二个参数仅作为配置文件丢失时的“最后防线(Fallback)”。
        # 如需修改任何字体、颜色或坐标，请永远只在 ui_config.toml 中修改。
        self.font_path = global_cfg.get("font_main", "./resources/SmileySans-Oblique.ttf")
        self.font_clock_path = global_cfg.get("font_clock", "./resources/bazaronite.ttf")
        self.font_icon_path = global_cfg.get("font_icon", "./resources/MaterialIcons-Regular.ttf")
        self.default_cover_path = global_cfg.get("default_cover", "./resources/default.png")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        def resolve_path(p):
            if not p: return p
            p = os.path.expanduser(str(p))
            if not os.path.isabs(p):
                return os.path.normpath(os.path.join(base_dir, p))
            return os.path.normpath(p)
            
        self.font_path = resolve_path(self.font_path)
        self.font_clock_path = resolve_path(self.font_clock_path)
        self.font_icon_path = resolve_path(self.font_icon_path)
        self.default_cover_path = resolve_path(self.default_cover_path)
        
        if not os.path.exists(self.default_cover_path):
            self.default_cover_path = resolve_path("default.png")

    def get_font(self, size):
        size = int(size)
        cache_key = (self.font_path, size)
        if cache_key not in _FONT_CACHE:
            try:
                _FONT_CACHE[cache_key] = ImageFont.truetype(self.font_path, size)
            except Exception as e:
                logger.warning(f"无法加载字体 {self.font_path}: {e}")
                _FONT_CACHE[cache_key] = ImageFont.load_default()
        return _FONT_CACHE[cache_key]

    def get_clock_font(self, size):
        size = int(size)
        cache_key = (self.font_clock_path, size)
        if cache_key not in _CLOCK_FONT_CACHE:
            try:
                _CLOCK_FONT_CACHE[cache_key] = ImageFont.truetype(self.font_clock_path, size)
            except Exception as e:
                logger.warning(f"无法加载时钟字体 {self.font_clock_path}: {e}")
                _CLOCK_FONT_CACHE[cache_key] = self.get_font(size)
        return _CLOCK_FONT_CACHE[cache_key]

    def get_icon_font(self, size):
        size = int(size)
        cache_key = (self.font_icon_path, size)
        if cache_key not in _ICON_FONT_CACHE:
            try:
                _ICON_FONT_CACHE[cache_key] = ImageFont.truetype(self.font_icon_path, size)
            except Exception as e:
                logger.warning(f"无法加载图标字体 {self.font_icon_path}: {e}")
                _ICON_FONT_CACHE[cache_key] = ImageFont.load_default()
        return _ICON_FONT_CACHE[cache_key]

    def hex_to_rgb(self, hex_color, default="white"):
        if not hex_color:
            return default
        hex_color = hex_color.lstrip('#')
        if len(hex_color) in (6, 8):
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return default
