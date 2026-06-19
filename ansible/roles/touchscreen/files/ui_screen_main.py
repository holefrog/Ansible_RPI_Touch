import time
import os
from PIL import Image, ImageDraw, ImageFilter, ImageStat
import logging
from ui_core import BaseUIRenderer

class MainUIRenderer(BaseUIRenderer):
    def __init__(self, display_ctx, ui_config):
        super().__init__(display_ctx, ui_config)
        self.cached_cover_key = None
        self.cached_bg_img = None
        self.logger = logging.getLogger("MainUI")
        # 新增文字渲染缓存，解决高频重绘卡顿
        self.cached_title_text = None
        self.cached_title_img = None
        self.cached_title_w = 0
        self.cached_album_raw = None
        self.cached_album_final = None
        self.cached_artist_text = None
        self.cached_artist_x = 0

    @staticmethod
    def format_time(seconds):
        secs = int(seconds)
        mins = secs // 60
        secs = secs % 60
        return f"{mins:02d}:{secs:02d}"

    def render(self, player_state):
        """渲染主播放界面"""
        img = Image.new("RGB", (self.width, self.height), "black")
        
        main_cfg = self.config.get("screens", {}).get("main", {})
        
        def get_centered_x(text, font):
            bbox = draw.textbbox((0, 0), text, font=font)
            return (self.width - (bbox[2] - bbox[0])) // 2
            
        # 1. 绘制背景 (使用缓存避免重复的高开销 Resize 和 Blend 计算)
        cover_path = getattr(player_state, "cover_path", None)
        if not cover_path or not os.path.exists(cover_path):
            cover_path = self.default_cover_path
            
        try:
            cover_mtime = os.path.getmtime(cover_path)
        except OSError:
            cover_mtime = 0
            
        album_text = getattr(player_state, "album", "")
        artist_text = player_state.top_text or ""
        current_cover_key = (cover_path, cover_mtime, album_text, artist_text)
            
        # 如果封面路径、文件修改时间或静态文本(专辑/歌手)改变，重新生成基础画板
        if self.cached_cover_key != current_cover_key or self.cached_bg_img is None:
            try:
                bg_cfg = main_cfg.get("background", {})
                bg_img = Image.open(cover_path).convert("RGB")
                
                # Letterbox / Contain 模式
                img_w, img_h = bg_img.size
                ratio = min(self.width / img_w, self.height / img_h)
                new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                
                bg_img = bg_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # --- 计算封面亮度 ---
                stat = ImageStat.Stat(bg_img.convert("L"))
                avg_brightness = stat.mean[0]
                
                letterbox_bg = Image.new("RGB", (self.width, self.height), "black")
                offset_x = (self.width - new_w) // 2
                offset_y = (self.height - new_h) // 2
                letterbox_bg.paste(bg_img, (offset_x, offset_y))

                # 根据配置决定是否应用高斯模糊
                blur_radius = bg_cfg.get("blur_radius", 0)
                if blur_radius > 0:
                    processed_bg = letterbox_bg.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                else:
                    processed_bg = letterbox_bg

                # 混合一层半透明黑色以突出文字
                overlay_color_hex = bg_cfg.get("overlay_color", "#00000066")
                overlay_alpha = int(overlay_color_hex[7:], 16) if len(overlay_color_hex) > 7 else 102
                
                # 动态自适应遮罩
                if avg_brightness > 120:
                    extra_darkness = int((avg_brightness - 120) / 135.0 * 120)
                    overlay_alpha = min(230, overlay_alpha + extra_darkness)
                    
                final_bg = Image.new("RGB", (self.width, self.height), self.hex_to_rgb(overlay_color_hex[:7]))
                final_bg = Image.blend(processed_bg, final_bg, alpha=overlay_alpha / 255.0)
                
                # ==========================================
                # 终极性能优化：将静态的专辑和歌手文字（及其阴影特效）直接“烤”进背景图里！
                # 这样每帧可以省去 4 次昂贵的 draw.text 调用，彻底根除抖动！
                # ==========================================
                bg_draw = ImageDraw.Draw(final_bg)
                
                # 烤入专辑 (Album)
                if album_text:
                    album_cfg = main_cfg.get("album", {})
                    album_font = self.get_font(album_cfg.get("font_size", 24))
                    album_color = self.hex_to_rgb(album_cfg.get("color", "#1DB954")) 
                    album_y = album_cfg.get("pos", [0, 75])[1]
                    
                    final_album_text = album_text
                    bbox = bg_draw.textbbox((0, 0), final_album_text, font=album_font)
                    max_title_width = self.width - 40
                    if (bbox[2] - bbox[0]) > max_title_width:
                        while len(final_album_text) > 0:
                            bbox = bg_draw.textbbox((0, 0), final_album_text + "...", font=album_font)
                            if (bbox[2] - bbox[0]) <= max_title_width: break
                            final_album_text = final_album_text[:-1]
                        final_album_text += "..."
                        
                    album_x = (self.width - (bbox[2] - bbox[0])) // 2
                    bg_draw.text((album_x + 1, album_y + 1), final_album_text, font=album_font, fill=(0, 0, 0))
                    bg_draw.text((album_x, album_y), final_album_text, font=album_font, fill=album_color)

                # 烤入艺术家/状态 (Artist)
                if artist_text:
                    artist_cfg = main_cfg.get("artist", {})
                    artist_font = self.get_font(artist_cfg.get("font_size", 22))
                    artist_color = self.hex_to_rgb(artist_cfg.get("color", "#B3B3B3"))
                    artist_y = artist_cfg.get("pos", [0, 195])[1]
                    
                    bbox = bg_draw.textbbox((0, 0), artist_text, font=artist_font)
                    artist_x = (self.width - (bbox[2] - bbox[0])) // 2
                    bg_draw.text((artist_x + 1, artist_y + 1), artist_text, font=artist_font, fill=(0, 0, 0))
                    bg_draw.text((artist_x, artist_y), artist_text, font=artist_font, fill=artist_color)

                self.cached_bg_img = final_bg
                self.cached_cover_key = current_cover_key
            except Exception as e:
                self.logger.error(f"无法加载封面 {cover_path}: {e}")
                self.cached_bg_img = Image.new("RGB", (self.width, self.height), "black")
                self.cached_cover_key = current_cover_key
        
        # 使用缓存的背景作为基础画板
        img.paste(self.cached_bg_img, (0, 0))
        draw = ImageDraw.Draw(img)
        
        # 2. 绘制标题
        title_cfg = main_cfg.get("title", {})
        title_font = self.get_font(title_cfg.get("font_size", 46))
        title_color = self.hex_to_rgb(title_cfg.get("color", "#FFFFFF"))
        title_text = player_state.bottom_text or "Unknown"
        
        max_title_width = self.width - 40  # 左右各留 20px padding
        title_y = title_cfg.get("pos", [0, 85])[1]  # 向上移动到 85
        
        # 增加歌名图像缓存：整体加完特效后生成图片再滚动
        # 避免每帧执行 draw.text 产生大量内存垃圾触发 GC 卡顿
        if self.cached_title_text != title_text:
            bbox = draw.textbbox((0, 0), title_text, font=title_font)
            text_w = bbox[2] - bbox[0]
            # 给高度留足余量，防止英文的下沉部分 (如 g, y, p) 被裁剪
            img_h = max(bbox[3] + 10, int(title_cfg.get("font_size", 46) * 1.5))
            
            txt_img = Image.new("RGBA", (text_w + 10, img_h), (0,0,0,0))
            txt_draw = ImageDraw.Draw(txt_img)
            # 绘制阴影 (稍微偏移，使用半透明黑色)
            txt_draw.text((2, 2), title_text, font=title_font, fill=(0, 0, 0, 160))
            # 绘制前景
            txt_draw.text((0, 0), title_text, font=title_font, fill=title_color)
            
            self.cached_title_text = title_text
            self.cached_title_img = txt_img
            self.cached_title_w = text_w
        
        if self.cached_title_w <= max_title_width:
            # 未超长，正常居中显示
            title_x = (self.width - self.cached_title_w) // 2
            img.paste(self.cached_title_img, (title_x, title_y), self.cached_title_img)
        else:
            # 超长文本，水平向左无缝平滑滚动 (Marquee)
            scroll_speed = self.ctx.get("marquee_speed", 50)
            gap = 100          # 两次循环文字之间的留白宽度
            total_w = self.cached_title_w + gap
            
            # 根据当前系统绝对时间计算当前平移的 offset
            offset = int(time.time() * scroll_speed) % total_w
            
            # 固定起始 X 坐标为 20 (padding)
            start_x = 20 - offset
            
            # 利用预渲染的缓存图像进行贴图覆盖，彻底杜绝 GC 抖动
            img.paste(self.cached_title_img, (start_x, title_y), self.cached_title_img)
            img.paste(self.cached_title_img, (start_x + total_w, title_y), self.cached_title_img)
        
        # 4. 绘制进度条
        pb_cfg = main_cfg.get("progress_bar", {})
        pb_x, pb_y = pb_cfg.get("pos", [20, 262])
        pb_w = pb_cfg.get("width", 440)
        pb_h = pb_cfg.get("height", 3)
        pb_bg = self.hex_to_rgb(pb_cfg.get("bg_color", "#4D4D4D"))
        pb_fill = self.hex_to_rgb(pb_cfg.get("fill_color", "#1DB954")) # 使用主题色更好
        
        draw.rectangle((pb_x, pb_y, pb_x + pb_w, pb_y + pb_h), fill=pb_bg)
        
        # 获取进度
        time_curr = getattr(player_state, "time_current", 0.0)
        time_tot = getattr(player_state, "time_total", 0.0)
        
        if time_tot > 0:
            ratio = min(max(time_curr / time_tot, 0.0), 1.0)
            curr_w = int(pb_w * ratio)
            draw.rectangle((pb_x, pb_y, pb_x + curr_w, pb_y + pb_h), fill=pb_fill)
            
            # 绘制纯白进度滑块圆点，增加可拖拽的高级视觉暗示
            knob_r = 6
            knob_cx = pb_x + curr_w
            knob_cy = pb_y + pb_h // 2
            draw.ellipse((knob_cx - knob_r, knob_cy - knob_r, knob_cx + knob_r, knob_cy + knob_r), fill=(255, 255, 255))
        
        # 5. 绘制时间
        curr_time_cfg = main_cfg.get("current_time", {})
        curr_font = self.get_font(curr_time_cfg.get("font_size", 14))
        curr_color = self.hex_to_rgb(curr_time_cfg.get("color", "#B3B3B3"))
        draw.text(tuple(curr_time_cfg.get("pos", [20, 275])), self.format_time(time_curr), font=curr_font, fill=curr_color)
        
        tot_time_cfg = main_cfg.get("total_time", {})
        tot_font = self.get_font(tot_time_cfg.get("font_size", 14))
        tot_color = self.hex_to_rgb(tot_time_cfg.get("color", "#B3B3B3"))
        draw.text(tuple(tot_time_cfg.get("pos", [400, 275])), self.format_time(time_tot), font=tot_font, fill=tot_color)

        return img
