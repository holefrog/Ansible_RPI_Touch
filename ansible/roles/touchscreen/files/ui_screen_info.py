import time
from PIL import Image, ImageDraw
from ui_core import BaseUIRenderer

class InfoScreenRenderer(BaseUIRenderer):
    def render(self, system_info, services_status):
        img = Image.new("RGB", (self.width, self.height), "black")
        draw = ImageDraw.Draw(img)

        info_cfg = self.config.get("screens", {}).get("info", {})

        def draw_cfg_text(cfg_key, text, default_pos, default_font_size, default_color, is_icon=False, is_brand=False, default_align="left"):
            cfg = info_cfg.get(cfg_key, {})
            if is_icon:
                font = self.get_icon_font(cfg.get("font_size", default_font_size))
            elif is_brand:
                font = self.get_icon_font(cfg.get("font_size", default_font_size))
            else:
                font = self.get_font(cfg.get("font_size", default_font_size))
            color = self.hex_to_rgb(cfg.get("color", default_color))
            pos = tuple(cfg.get("pos", default_pos))
            align = cfg.get("align", default_align)

            if align == "right":
                if hasattr(draw, "textlength"):
                    tw = draw.textlength(text, font=font)
                else:
                    tw = draw.textsize(text, font=font)[0]
                draw.text((pos[0] - tw, pos[1]), text, font=font, fill=color)
            else:
                draw.text(pos, text, font=font, fill=color)


        # 2. Left column (Services Status)
        draw_cfg_text("status_title", "System Status", [20, 68], 16, "#1DB954")

        service_configs = [
            ("service_squeezelite", "Squeezelite", "squeezelite"),
            ("service_airplay", "AirPlay", "shairport-sync"),
            ("service_bluetooth", "Bluetooth", "bluetooth"),
            ("service_autopair", "BT Pair", "bluetooth-a2dp-autopair"),
            ("service_pipewire", "PipeWire", "pipewire"),
            ("service_wireplumber", "WirePlumber", "wireplumber"),
            ("service_volume", "Volume", "volume"),
            ("service_wyoming", "Wyoming", "wyoming_all")
        ]

        # 计算 Wyoming 综合状态
        services_status["wyoming_all"] = (
            services_status.get("wyoming-porcupine1", False) and
            services_status.get("wyoming-whisper", False) and
            services_status.get("wyoming-piper", False) and
            services_status.get("wyoming-satellite", False)
        )

        for i, (cfg_key, label, svc_key) in enumerate(service_configs):
            cfg = info_cfg.get(cfg_key, {})
            pos = cfg.get("pos", [20, 96 + i * 24])
            font_size = cfg.get("font_size", 14)
            color = self.hex_to_rgb(cfg.get("color", "#B3B3B3"))
            font = self.get_font(font_size)

            is_active = services_status.get(svc_key, False)
            status_color_hex = cfg.get("status_color", "#1DB954") if is_active else "#E74C3C"
            status_color = self.hex_to_rgb(status_color_hex)

            # draw circle
            r = 5
            cx, cy = pos[0] + 6, pos[1] + font_size//2
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=status_color)

            # draw text
            draw.text((pos[0] + 18, pos[1]-2), label, font=font, fill=color)

        # 3. Right column top (Network Interfaces)
        draw_cfg_text("network_title", "Network Interfaces", [238, 68], 16, "#1DB954")
        draw_cfg_text("eth0_label", "Wired (eth0)", [238, 92], 12, "#B3B3B3")
        draw_cfg_text("eth0_ip", system_info.get("eth0_ip", "N/A"), [238, 110], 14, "#FFFFFF")
        draw_cfg_text("wlan0_label", "Wireless (wlan0)", [238, 134], 12, "#B3B3B3")
        draw_cfg_text("wlan0_ip", system_info.get("wlan0_ip", "N/A"), [238, 152], 14, "#FFFFFF")

        # 4. Right column bottom (System Info)
        draw_cfg_text("system_title", "System Info", [238, 185], 16, "#1DB954")

        labels_cfg = info_cfg.get("sys_labels", {})
        l_font = self.get_font(labels_cfg.get("font_size", 12))
        l_color = self.hex_to_rgb(labels_cfg.get("color", "#B3B3B3"))
        lx, ly = labels_cfg.get("pos", [238, 212])
        dy = 18

        labels = ["CPU (Temp/Usage)", "RAM Usage", "Disk Usage", "Render (SPI/FPS)"]
        for i, lbl in enumerate(labels):
            draw.text((lx, ly + i*dy), lbl, font=l_font, fill=l_color)

        # cpu (temp + usage)
        cpu_temp = system_info.get('cpu_temp', 0)
        cpu_usage = system_info.get('cpu_usage', 0)
        draw_cfg_text("cpu_val", f"{cpu_temp:.1f}°C / {cpu_usage:.1f}%", [460, 212], 12, "#FFFFFF", default_align="right")

        # ram_usage
        rt = system_info.get('ram_total', 1)
        ru = system_info.get('ram_used', 0)
        rp = (ru/rt)*100 if rt > 0 else 0
        rt_mb, ru_mb = rt/(1024**2), ru/(1024**2)
        draw_cfg_text("ram_usage_val", f"{ru_mb:.0f}MB/{rt_mb/1024:.1f}GB ({rp:.0f}%)", [460, 230], 12, "#FFFFFF", default_align="right")

        # disk_usage
        dt = system_info.get('disk_total', 1)
        du = system_info.get('disk_used', 0)
        dp = (du/dt)*100 if dt > 0 else 0
        dt_gb, du_gb = dt/(1024**3), du/(1024**3)
        draw_cfg_text("disk_usage_val", f"{du_gb:.1f}GB/{dt_gb:.1f}GB ({dp:.0f}%)", [460, 248], 12, "#FFFFFF", default_align="right")
        
        # render perf
        spi_time = system_info.get('spi_time_ms', 0)
        fps = system_info.get('fps', 0)
        draw_cfg_text("perf_val", f"{spi_time:.1f}ms / {fps:.1f} fps", [460, 266], 12, "#FFFFFF", default_align="right")

        # 5. Divider
        div_cfg = info_cfg.get("divider", {})
        d_start = tuple(div_cfg.get("start_pos", [228, 68]))
        d_end = tuple(div_cfg.get("end_pos", [228, 290]))
        d_color = self.hex_to_rgb(div_cfg.get("color", "#4D4D4D"))
        draw.line([d_start, d_end], fill=d_color, width=1)

        return img
