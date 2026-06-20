#!/usr/bin/env python
# ui_screen_assistant.py

import time
import math
from PIL import Image, ImageDraw, ImageFont
from ui_core import BaseUIRenderer

class AssistantScreenRenderer(BaseUIRenderer):
    """
    智能助手全屏浮层渲染器
    负责绘制唤醒等待、文字识别、以及播放 TTS 时的动画和文字。
    """
    def render(self, base_img, voice_state, transcript_text):
        """
        Args:
            base_img: 底层图像
            voice_state: str ("listening", "processing", "speaking")
            transcript_text: str 当前识别到的文字
        """
        # 1. 创建半透明遮罩背景 (稍微深一点，突出语音界面)
        overlay = Image.new("RGBA", (self.width, self.height), (15, 15, 20, 230))
        draw = ImageDraw.Draw(overlay)
        
        center_x = self.width // 2
        
        # 2. 动画时间计算
        t = time.time()
        
        # 3. 绘制上方状态图标/动画
        icon_y = 120
        try:
            icon_font = self.get_icon_font(60)
        except IOError:
            icon_font = ImageFont.load_default()
            
        if voice_state == "listening":
            # 呼吸灯效果的麦克风
            breath = (math.sin(t * 4) + 1) / 2 # 0 to 1
            color = (29, 185, 84, int(150 + 105 * breath)) # 绿色呼吸
            icon_char = "\ue029" # microphone icon
            
            # 画一个圆圈背景
            radius = 50 + 10 * breath
            draw.ellipse((center_x - radius, icon_y - radius, center_x + radius, icon_y + radius), 
                         fill=(29, 185, 84, 40))
                         
        elif voice_state == "processing":
            # 旋转/转圈提示
            color = (100, 150, 255, 255) # 蓝色
            icon_char = "\ue029" # 还是麦克风，可以换成别的
            # 转圈动画
            angle = (t * 360) % 360
            draw.arc((center_x - 50, icon_y - 50, center_x + 50, icon_y + 50), 
                     start=angle, end=angle+270, fill=(100, 150, 255, 200), width=6)
                     
        elif voice_state == "speaking":
            # 声波动画的喇叭
            color = (255, 180, 50, 255) # 橙色
            icon_char = "\ue050" # volume_up
            
            wave_count = int((t * 5) % 4)
            # 简单模拟声波
            for i in range(wave_count):
                draw.arc((center_x - 50, icon_y - 50, center_x + 50, icon_y + 50),
                         start=-45, end=45, fill=(255, 180, 50, 150), width=4)
        else:
            color = (255, 255, 255, 255)
            icon_char = "\ue029"

        # 居中绘制 Icon
        if hasattr(draw, "textlength"):
            icon_w = draw.textlength(icon_char, font=icon_font)
        else:
            icon_w = draw.textsize(icon_char, font=icon_font)[0]
            
        draw.text((center_x - icon_w // 2, icon_y - 30), icon_char, font=icon_font, fill=color)

        # 4. 绘制提示文字或识别内容
        if not transcript_text:
            if voice_state == "listening":
                display_text = "小派听候指示..."
            elif voice_state == "processing":
                display_text = "正在处理..."
            elif voice_state == "speaking":
                display_text = "已收到"
            else:
                display_text = ""
        else:
            display_text = transcript_text

        text_font = self.get_font(24)
        
        if hasattr(draw, "textlength"):
            text_w = draw.textlength(display_text, font=text_font)
        else:
            text_w = draw.textsize(display_text, font=text_font)[0]
            
        # 如果文字过长，简单截断或者靠左（这里为简单起见，做个基础居中）
        x_pos = max(10, center_x - text_w // 2)
        draw.text((x_pos, 220), display_text, font=text_font, fill=(255, 255, 255, 255))

        # 合成到底图
        final_img = base_img.convert("RGBA")
        final_img.alpha_composite(overlay)
        return final_img.convert("RGB")
