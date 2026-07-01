import time
import logging
from PIL import ImageDraw
from ui_core import BaseUIRenderer
from ui_components import draw_badge

logger = logging.getLogger("StatusBarUI")

class StatusBarRenderer(BaseUIRenderer):
    def render(self, img, player_state=None, active_button=None, current_screen=None):
        """
        在给定的 img 上绘制全局状态栏
        """
        draw = ImageDraw.Draw(img)
        status_cfg = self.config.get("screens", {}).get("status_top", {})
        
        # WIFI
        wifi_cfg = status_cfg.get("wifi", {})
        if wifi_cfg:
            base_size = wifi_cfg.get("font_size", 14)
            wifi_font = self.get_font(base_size)
            wifi_icon_font = self.get_icon_font(base_size + 6) # 图标比文字大 6px
            wifi_color = self.hex_to_rgb(wifi_cfg.get("color", "#B3B3B3"))
            icon_conn = wifi_cfg.get("icon_connected", "\uf1eb")
            icon_disc = wifi_cfg.get("icon_disconnected", "\uf00d")
            
            try:
                # 增加缓存，防止 Wi-Fi 信号每秒都在波动，导致顶部状态栏每帧都是“脏区”
                # 这会引发灾难性的全屏 SPI 刷新，直接拖垮 FPS 到 17 左右
                current_t = time.time()
                if not hasattr(self, '_last_wifi_update') or (current_t - self._last_wifi_update > 5):
                    from query_system import get_wifi_quality
                    self._cached_connected, self._cached_quality = get_wifi_quality()
                    self._last_wifi_update = current_t
                connected = self._cached_connected
                quality = self._cached_quality
            except:
                connected = False
                quality = 0
                
            wifi_pos = tuple(wifi_cfg.get("pos", [20, 26]))
            text_y_offset = 3 # 文字向下微调对齐图标中心
            
            if connected:
                # 每 5 秒才更新一次字符串，避免无谓的局部重绘
                wifi_str = f" {quality}%"
                draw.text(wifi_pos, icon_conn, font=wifi_icon_font, fill=wifi_color)
                
                # 兼容不同版本 PIL 测量宽度
                icon_w = draw.textlength(icon_conn, font=wifi_icon_font) if hasattr(draw, 'textlength') else (
                    draw.textbbox((0,0), icon_conn, font=wifi_icon_font)[2] if hasattr(draw, 'textbbox') else draw.textsize(icon_conn, font=wifi_icon_font)[0]
                )
                
                draw.text((wifi_pos[0] + icon_w, wifi_pos[1] + text_y_offset), wifi_str, font=wifi_font, fill=wifi_color)
            else:
                # 未连接时，只显示一个断开的图标
                draw.text(wifi_pos, icon_disc, font=wifi_icon_font, fill=wifi_color)
            
        # Volume
        vol_cfg = status_cfg.get("volume", {})
        if vol_cfg and player_state and player_state.volume >= 0:
            base_size = vol_cfg.get("font_size", 14)
            vol_font = self.get_font(base_size)
            vol_icon_font = self.get_icon_font(base_size + 6)
            vol_color = self.hex_to_rgb(vol_cfg.get("color", "#B3B3B3"))
            
            vol_pos = tuple(vol_cfg.get("pos", [85, 26]))
            vol_icon = vol_cfg.get("icon", "\ue050") # 修正备用图标
            vol_str = f" {player_state.volume}%"
            text_y_offset = 3
            
            draw.text(vol_pos, vol_icon, font=vol_icon_font, fill=vol_color)
            
            icon_w = draw.textlength(vol_icon, font=vol_icon_font) if hasattr(draw, 'textlength') else (
                    draw.textbbox((0,0), vol_icon, font=vol_icon_font)[2] if hasattr(draw, 'textbbox') else draw.textsize(vol_icon, font=vol_icon_font)[0]
                )
                
            draw.text((vol_pos[0] + icon_w, vol_pos[1] + text_y_offset), vol_str, font=vol_font, fill=vol_color)
            
        # Info icon
        info_cfg = status_cfg.get("info_icon", {})
        if info_cfg and current_screen != "info":
            info_icon_font = self.get_icon_font(info_cfg.get("font_size", 14) + 6)
            if active_button == "info":
                info_color = (255, 255, 255)  # 激活时高亮变白
            else:
                info_color = self.hex_to_rgb(info_cfg.get("color", "#B3B3B3"))
            info_pos = tuple(info_cfg.get("pos", [150, 26]))
            info_icon = info_cfg.get("icon", "\ue88e") # 修正备用图标
            draw.text(info_pos, info_icon, font=info_icon_font, fill=info_color)
            
        # 时间 (居中)
        time_cfg = status_cfg.get("time", {})
        time_font = self.get_font(time_cfg.get("font_size", 32))
        time_color = self.hex_to_rgb(time_cfg.get("color", "#FFFFFF"))
        time_str = time.strftime("%H:%M")
        
        if hasattr(draw, 'textbbox'):
            bbox_time = draw.textbbox((0, 0), time_str, font=time_font)
            w_time = bbox_time[2] - bbox_time[0]
        else:
            w_time = draw.textsize(time_str, font=time_font)[0]
            
        x_time = (self.width - w_time) // 2
        y_time = time_cfg.get("pos", [0, 15])[1]
        draw.text((x_time, y_time), time_str, font=time_font, fill=time_color)
        
        # 重启按钮 (只在 Info 界面可见)
        reboot_cfg = status_cfg.get("reboot", {})
        if reboot_cfg and current_screen == "info":
            reboot_pos = tuple(reboot_cfg.get("pos", [385, 26]))
            reboot_size = reboot_cfg.get("font_size", 14) + 6
            reboot_color = self.hex_to_rgb(reboot_cfg.get("color", "#E74C3C"))
            reboot_icon = reboot_cfg.get("icon", "\ue8ac")
            
            try:
                reboot_font = self.get_icon_font(reboot_size)
                draw.text(reboot_pos, reboot_icon, font=reboot_font, fill=reboot_color)
            except Exception as e:
                logger.warning(f"无法绘制重启图标: {e}")

        
        # 相册入口图标
        photo_cfg = status_cfg.get("photo_icon", {})
        # 仅在播放或暂停时显示
        if photo_cfg and player_state and not player_state.is_clock:
            photo_pos = tuple(photo_cfg.get("pos", [345, 26]))
            photo_size = photo_cfg.get("font_size", 14) + 6 # 同步调大图标
            photo_color = self.hex_to_rgb(photo_cfg.get("color", "#B3B3B3"))
            photo_icon = photo_cfg.get("icon", "\ue410") # 修正备用图标

            try:
                photo_font = self.get_icon_font(photo_size)
                draw.text(photo_pos, photo_icon, font=photo_font, fill=photo_color)
            except Exception as e:
                logger.warning(f"无法绘制相册图标: {e}")
                px, py = photo_pos
                draw.rectangle((px, py, px + 16, py + 12), outline=photo_color, width=1)
                draw.polygon([(px, py + 12), (px + 5, py + 5), (px + 10, py + 10), (px + 16, py + 4), (px + 16, py + 12)], fill=photo_color)
                draw.ellipse((px + 3, py + 3, px + 6, py + 6), fill=photo_color)

        # 右上角播放器标识 (Badge)
        # 仅在有明确的活跃播放器时显示
        if player_state and player_state.active_player_type and not player_state.is_clock:
            badge_cfg = status_cfg.get("source_badge", {})
            badge_icons = badge_cfg.get("icons", {})

            badge_info = {
                "squeezelite": (badge_icons.get("squeezelite", "\uf8f9"), "Squeeze"),
                "airplay": (badge_icons.get("airplay", "\ue055"), "AirPlay"),
                "bluetooth": (badge_icons.get("bluetooth", "\ue1a7"), "Bluetooth")
            }
            icon_char, text_str = badge_info.get(player_state.active_player_type, (badge_icons.get("default", "\ue037"), "Player"))

            # 调用全局统一的组件进行绘制
            draw_badge(draw, self, badge_cfg, icon_char, text_str)
        
        return img
