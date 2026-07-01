import time
from PIL import Image, ImageDraw
from ui_core import BaseUIRenderer

class ScreenSaverRenderer(BaseUIRenderer):
    def _draw_text_with_glow(self, img, draw, pos, text, font, fill_color, glow_color, is_nixie=False):
        """Helper to draw text with a soft glow/shadow effect."""
        if is_nixie and glow_color:
            try:
                # 真实的真空管/辉光管渲染逻辑 (多层气体辉光模拟)
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                pad = 40  # 增加 padding 容纳更大的霓虹晕染
                
                from PIL import ImageFilter
                # --- 1. 使用 L 模式绘制掩码 (完美解决 RGBA 模糊导致的发黑与亮度衰减问题) ---
                mask_img = Image.new("L", (w + pad * 2, h + pad * 2), 0)
                mask_draw = ImageDraw.Draw(mask_img)
                mask_draw.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=255)
                
                # 模糊掩码得到辉光透明度渐变
                outer_mask = mask_img.filter(ImageFilter.GaussianBlur(radius=12))
                inner_mask = mask_img.filter(ImageFilter.GaussianBlur(radius=3))
                
                # --- 2. 创建高亮度纯色图层 ---
                outer_solid = Image.new("RGB", (w + pad * 2, h + pad * 2), glow_color[:3])
                
                # 模拟紧贴灯丝的高温发光气体，软化字体边缘
                r1, g1, b1 = fill_color[:3]
                r2, g2, b2 = glow_color[:3]
                inner_color = ((r1+r2*2)//3, (g1+g2*2)//3, (b1+b2*2)//3)
                inner_solid = Image.new("RGB", (w + pad * 2, h + pad * 2), inner_color)
                
                paste_x = int(pos[0]) - pad + bbox[0]
                paste_y = int(pos[1]) - pad + bbox[1]
                
                # 叠加高斯模糊辉光层到主图
                # 外层霓虹辉光 (Nixie管光晕极强，外层叠加两次以增加浓度)
                img.paste(outer_solid, (paste_x, paste_y), outer_mask)
                img.paste(outer_solid, (paste_x, paste_y), outer_mask)
                
                # 内层高温发光气体
                img.paste(inner_solid, (paste_x, paste_y), inner_mask)
                
                # 3. 绘制最核心的高亮灯丝前景
                draw.text(pos, text, font=font, fill=fill_color)
            except Exception as e:
                # 若高级渲染失败，退化为普通渲染保证时钟可见
                draw.text(pos, text, font=font, fill=fill_color)
                
        elif glow_color:
            # 动态获取字体大小，按比例计算霓虹辉光（描边）的厚度
            font_size = getattr(font, "size", 30)
            stroke_w = max(1, int(font_size * 0.04))
            draw.text(pos, text, font=font, fill=fill_color, stroke_width=stroke_w, stroke_fill=glow_color)
        else:
            draw.text(pos, text, font=font, fill=fill_color)

    def render(self, current_time_str, current_date_str, is_dimmed=False):
        """渲染屏保模式"""
        img = Image.new("RGB", (self.width, self.height), "black")
        draw = ImageDraw.Draw(img)
        
        screensaver_cfg = self.config.get("screens", {}).get("screensaver", {})
        
        def get_centered_x(text, font):
            bbox = draw.textbbox((0, 0), text, font=font)
            return (self.width - (bbox[2] - bbox[0])) // 2
        
        # 绘制时间
        time_cfg = screensaver_cfg.get("time", {})
        time_font_size = time_cfg.get("font_size", 138)
        time_font = self.get_clock_font(time_font_size)
        time_color = self.hex_to_rgb(time_cfg.get("color", "#FFFFFF"))
        glow_color = self.hex_to_rgb(time_cfg.get("glow_color"))
        
        # 获取时间组件
        t = time.localtime()
        hour_str = time.strftime("%H", t)
        minute_str = time.strftime("%M", t)
        sec_str = time.strftime("%S", t)
        show_colon = (int(time.time()) % 2 == 0)
        
        # 获取基础物理圆心 (如果配置了网格，使用网格中心，否则使用屏幕正中心)
        grid_cfg = screensaver_cfg.get("background_grid", {})
        cx, cy = grid_cfg.get("center", [240, 160]) if grid_cfg else (self.width // 2, self.height // 2)

        # 0. 绘制背景科技感雷达网格与 60秒 进度表现
        if grid_cfg:
            r_max = grid_cfg.get("radius_max", 150)
            grid_color = self.hex_to_rgb(grid_cfg.get("color", "#4D4D4D"))
            sweep_color = self.hex_to_rgb(grid_cfg.get("sweep_color", "#1DB954"))
            
            # 画同心圆与十字准星
            for r in [r_max, int(r_max * 0.75), int(r_max * 0.5)]:
                draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=grid_color, width=1)
            draw.line((cx - r_max - 15, cy, cx + r_max + 15, cy), fill=grid_color, width=1)
            draw.line((cx, cy - r_max - 15, cx, cy + r_max + 15), fill=grid_color, width=1)
            
            # 科幻雷达扫描秒针（带拖尾余辉）
            import math
            curr_sec = time.time() % 60
            angle = -math.pi / 2 + (curr_sec / 60.0) * 2 * math.pi
            
            trail_angle = 120 # 拖尾角度（120度余辉）
            segments = 60     # 分成 60 个多边形切片（每 2 度一个）保证绝对平滑
            
            for i in range(segments):
                # 计算二次衰减曲线，让余辉自然消散，头端亮尾端暗
                progress = 1.0 - (i / float(segments))
                fade = (progress ** 2) * 0.85 # 提高余辉最高亮度
                
                # 直接按比例调暗 RGB 以模拟在黑色背景上的发光衰减
                r = int(sweep_color[0] * fade)
                g = int(sweep_color[1] * fade)
                b = int(sweep_color[2] * fade)
                
                a1 = angle - (i * (trail_angle / segments)) * math.pi / 180.0
                a2 = angle - ((i + 1) * (trail_angle / segments)) * math.pi / 180.0
                
                ex1 = cx + r_max * math.cos(a1)
                ey1 = cy + r_max * math.sin(a1)
                ex2 = cx + r_max * math.cos(a2)
                ey2 = cy + r_max * math.sin(a2)
                
                # 绘制无缝平滑的余辉切片多边形
                draw.polygon([(cx, cy), (ex1, ey1), (ex2, ey2)], fill=(r, g, b))
            
            # 绘制最亮的主扫描指针
            end_x = cx + r_max * math.cos(angle)
            end_y = cy + r_max * math.sin(angle)
            draw.line((cx, cy, end_x, end_y), fill=sweep_color, width=2)
            
            # 画一个中心实心圆点，让指针根部更稳重
            draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=sweep_color)

           
        # 冒号配置 (可独立配置颜色)
        colon_cfg = screensaver_cfg.get("time_colon", {})
        colon_font_size = colon_cfg.get("font_size", time_font_size)
        colon_font = self.get_clock_font(colon_font_size)
        colon_color = self.hex_to_rgb(colon_cfg.get("color", "#FFFFFF"))
        
        # 获得单根管子的物理步进跨度（减去10使其产生互锁的紧凑感）
        try:
            bbox_8 = time_font.getbbox("8")
        except AttributeError:
            if hasattr(draw, 'textbbox'):
                bbox_8 = draw.textbbox((0, 0), "8", font=time_font)
            else:
                ts = draw.textsize("8", font=time_font)
                bbox_8 = (0, 0, ts[0], ts[1])
                
        tube_spacing = self.get_text_size(draw, "8", time_font)[0] - 10
        colon_w = self.get_text_size(draw, ":", colon_font)[0]
        
        gap = 10  # 冒号两边的间距
        
        # 预先定义各个部件相对于起点 (0) 的相对坐标，保持完美的紧凑字间距
        rel_hour0 = 0
        rel_hour1 = tube_spacing
        
        # 为了抵消斜体字体在垂直居中位置产生的严重视觉不对称（左字上凸，右字下凹）
        # 我们手动给冒号增加一个向右的视觉补偿偏移，让它在两个倾斜管子的“视觉峡谷”中居中
        italic_visual_offset = 18
        rel_colon = rel_hour1 + tube_spacing + gap + italic_visual_offset
        
        # 分钟管子的起点。总跨度保持不变（扣除这 18 像素的补偿），保证整体紧凑
        rel_min0 = rel_hour1 + tube_spacing + colon_w + gap * 2
        rel_min1 = rel_min0 + tube_spacing
        
        # 计算整个时钟模块的“纯墨迹视觉外边缘”
        # 最左侧墨迹：左边第一个字(hour0)的墨迹起点
        ink_left = rel_hour0 + bbox_8[0]
        
        # 最右侧墨迹：右边最后一个字(min1)的墨迹终点
        ink_right = rel_min1 + bbox_8[2]
        
        # 整个时钟模块的纯墨迹中心必须绝对对准物理中心 cx
        # start_x + (ink_left + ink_right) / 2 = cx
        start_x = cx - (ink_left + ink_right) / 2.0
        
        # 赋予最终的绝对坐标
        hour_tube0_x = start_x + rel_hour0
        hour_tube1_x = start_x + rel_hour1
        colon_x = start_x + rel_colon
        minute_tube0_x = start_x + rel_min0
        minute_tube1_x = start_x + rel_min1
        
        # ==========================================
        # 用户终极纯视觉微调指令 (Optical Tuning)
        # 第一次: “冒号向左5。右边的整体向右20”
        # 第二次: “冒号和右边整体向右2。冒号向下2”
        # 综合 X 轴偏移计算：
        # ==========================================
        colon_x += (-5 + 2)
        minute_tube0_x += (20 + 2)
        minute_tube1_x += (20 + 2)
        
        def draw_tube(x, y, char_str, font, color, is_bg=False):
            if not char_str.strip(): return
            
            # 直接在同一坐标点绘制，完全依赖字体内部的排版设定
            # 这样诸如 "1" 这样的字符就会自动对齐到数码管的右侧，而不是被强制居中
            if is_bg:
                ghost_color = (max(10, int(color[0]*0.15)), max(10, int(color[1]*0.15)), max(10, int(color[2]*0.15)))
                draw.text((x, y), char_str, font=font, fill=ghost_color)
            else:
                self._draw_text_with_glow(img, draw, (x, y), char_str, font, color, glow_color, is_nixie=True)

        # 计算 Y 轴绝对居中坐标
        def get_y_offset(char, font):
            bbox = draw.textbbox((0, 0), char, font=font)
            return cy - (bbox[3] + bbox[1]) / 2.0
            
        time_y = get_y_offset("8", time_font)
        colon_y = get_y_offset(":", colon_font) + time_cfg.get("colon_offset_y", -5)
        colon_y += 6  # 用户二次微调：冒号向下6像素

        # 1. 绘制底层物理灯管 (全为 8 和 :)
        draw_tube(hour_tube0_x, time_y, "8", time_font, time_color, is_bg=True)
        draw_tube(hour_tube1_x, time_y, "8", time_font, time_color, is_bg=True)
        draw_tube(colon_x, colon_y, ":", colon_font, colon_color, is_bg=True)
        draw_tube(minute_tube0_x, time_y, "8", time_font, time_color, is_bg=True)
        draw_tube(minute_tube1_x, time_y, "8", time_font, time_color, is_bg=True)
        
        # 2. 绘制前景点亮灯丝
        if hour_str:
            draw_tube(hour_tube0_x, time_y, hour_str[0], time_font, time_color)
            if len(hour_str) > 1:
                draw_tube(hour_tube1_x, time_y, hour_str[1], time_font, time_color)
                
        if show_colon:
            draw_tube(colon_x, colon_y, ":", colon_font, colon_color)
            
        if minute_str:
            draw_tube(minute_tube0_x, time_y, minute_str[0], time_font, time_color)
            if len(minute_str) > 1:
                draw_tube(minute_tube1_x, time_y, minute_str[1], time_font, time_color)
        
        # 绘制日期
        date_cfg = screensaver_cfg.get("date", {})
        date_font_size = date_cfg.get("font_size", 28)
        date_font = self.get_font(date_font_size)
        date_color = self.hex_to_rgb(date_cfg.get("color", "#B3B3B3"))
        date_glow_color = self.hex_to_rgb(date_cfg.get("glow_color"))
        
        date_y = date_cfg.get("pos", [0, 230])[1]
        
        date_x = get_centered_x(current_date_str, date_font)
        self._draw_text_with_glow(img, draw, (date_x, date_y), current_date_str, date_font, date_color, date_glow_color)
        
        return img
