#!/usr/bin/env python
# ui_components.py

from PIL import ImageDraw

def draw_badge(draw, renderer, cfg, icon_char, text_str):
    """
    绘制一个带图标和文字的圆角矩形标签 (Badge)，并动态居中。
    这是一个可复用的 UI 组件。
    """
    base_size = cfg.get("font_size", 14)
    badge_font = renderer.get_font(base_size)
    i_font = renderer.get_icon_font(base_size + 4)  # 图标稍微比文字大一点点
    badge_bg = renderer.hex_to_rgb(cfg.get("color", "#1DB954"))
    badge_text_color = renderer.hex_to_rgb(cfg.get("text_color", "#FFFFFF"))

    # 计算两部分的总宽度
    if hasattr(draw, 'textbbox'):
        bbox_icon = draw.textbbox((0, 0), icon_char, font=i_font)
        bbox_text = draw.textbbox((0, 0), text_str, font=badge_font)
        w_icon = bbox_icon[2] - bbox_icon[0]
        w_text = bbox_text[2] - bbox_text[0]
        # 统一使用文字高度作为基准，并增加内边距
        bh = (bbox_text[3] - bbox_text[1]) + 8
    else:
        w_icon, h_icon = draw.textsize(icon_char, font=i_font)
        w_text, h_text = draw.textsize(text_str, font=badge_font)
        bh = h_text + 8

    # 内边距和间距
    padding_x = 8
    spacing = 4
    bw = w_icon + spacing + w_text + padding_x * 2

    # 动态靠右对齐：距离屏幕右侧边缘 15 像素
    bx = renderer.width - bw - 15
    by = cfg.get("pos", [0, 22])[1]

    # 背景
    draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=4, fill=badge_bg)

    # 垂直居中对齐
    icon_y = by + (bh - (draw.textbbox((0,0),icon_char,font=i_font)[3] - draw.textbbox((0,0),icon_char,font=i_font)[1])) // 2
    text_y = by + (bh - (draw.textbbox((0,0),text_str,font=badge_font)[3] - draw.textbbox((0,0),text_str,font=badge_font)[1])) // 2

    # 画图标和文字
    draw.text((bx + padding_x, icon_y), icon_char, font=i_font, fill=badge_text_color)
    draw.text((bx + padding_x + w_icon + spacing, text_y), text_str, font=badge_font, fill=badge_text_color)

def draw_bubble(draw, text, x, y, font, max_w, bg_color, text_color, is_user, padding):
    """
    绘制一个聊天气泡。
    这是一个可复用的 UI 组件。
    """
    # 简单的文本折行逻辑
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        # 使用 textbbox 测量宽度
        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
        else:
            w = draw.textsize(test_line, font=font)[0]

        if w <= (max_w - padding * 2):
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)

    # 计算总高度和最大宽度
    line_heights = []
    line_widths = []
    for line in lines:
        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])
        else:
            w, h = draw.textsize(line, font=font)
            line_widths.append(w)
            line_heights.append(h)

    bubble_w = max(line_widths) + padding * 2 if line_widths else padding * 2
    # 增加行间距 (假定为 4 像素)
    bubble_h = sum(line_heights) + (len(lines) - 1) * 4 + padding * 2 if lines else padding * 2

    # 如果是用户（靠右对齐），x 代表右边界；否则 x 代表左边界
    if is_user:
        rect_x = x - bubble_w
    else:
        rect_x = x

    # 绘制气泡背景
    draw.rounded_rectangle(
        (rect_x, y, rect_x + bubble_w, y + bubble_h),
        radius=8,
        fill=bg_color
    )

    # 绘制多行文本
    text_y = y + padding
    for i, line in enumerate(lines):
        draw.text((rect_x + padding, text_y), line, font=font, fill=text_color)
        text_y += line_heights[i] + 4

    return bubble_h