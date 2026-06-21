#!/usr/bin/env python
# ui_screen_assistant.py - Voice Assistant Chat Interface
# All colours, sizes and layout values come from ui_config.toml [screens.assistant].

import time
import math
from PIL import Image, ImageDraw
from ui_core import BaseUIRenderer


class AssistantScreenRenderer(BaseUIRenderer):
    """
    Full-screen voice-assistant chat interface driven entirely by ui_config.toml.
    """

    # ── Init: pull every constant from config once ───────────────────────────

    def __init__(self, display_ctx, ui_config):
        super().__init__(display_ctx, ui_config)

        cfg = ui_config.get("screens", {}).get("assistant", {})
        col = cfg.get("colors", {})

        # Layout geometry
        self.HEADER_H   = int(cfg.get("header_height",   46))
        self.FOOTER_H   = int(cfg.get("footer_height",   44))
        self.MARGIN     = int(cfg.get("margin",          12))
        self.PAD        = int(cfg.get("bubble_padding",   9))
        self.RADIUS     = int(cfg.get("bubble_radius",   11))
        self.LINE_GAP   = int(cfg.get("bubble_line_gap",  6))
        self.BUBBLE_GAP = int(cfg.get("bubble_gap",       8))
        self.MAX_TURNS  = int(cfg.get("max_turns",         5))
        self.DOT_R      = int(cfg.get("dot", {}).get("radius", 6))

        # Font sizes
        self.TITLE_FS  = int(cfg.get("title",       {}).get("font_size", 17))
        self.USER_FS   = int(cfg.get("user_bubble", {}).get("font_size", 16))
        self.ASST_FS   = int(cfg.get("asst_bubble", {}).get("font_size", 14))
        self.STATUS_FS = int(cfg.get("status",      {}).get("font_size", 14))

        # Title text
        self.TITLE_TEXT = cfg.get("title", {}).get("text", "Voice Assistant")

        # Mic icon
        mic_cfg = cfg.get("mic", {})
        self.MIC_SIZE     = int(mic_cfg.get("icon_size",    72))
        self.MIC_CHAR     = mic_cfg.get("icon_char", "\ue029")
        self.MIC_GLOW_DIV = int(mic_cfg.get("glow_divider",  5))

        # Colours – converted from hex to RGB tuples
        self.C_BG         = self.hex_to_rgb(cfg.get("bg_color",        "#080A12"))
        self.C_HEADER     = self.hex_to_rgb(cfg.get("header_bg_color", "#101424"))
        self.C_DIVIDER    = self.hex_to_rgb(cfg.get("divider_color",   "#23293D"))
        self.C_TITLE      = self.hex_to_rgb(cfg.get("title", {}).get("color", "#EBF0FA"))
        self.C_USER_BG    = self.hex_to_rgb(cfg.get("user_bubble", {}).get("bg_color", "#285ABE"))
        self.C_USER_TEXT  = self.hex_to_rgb(cfg.get("user_bubble", {}).get("text_color", "#EBF0FA"))
        self.C_ASST_BG    = self.hex_to_rgb(cfg.get("asst_bubble", {}).get("bg_color",  "#1A2032"))
        self.C_LISTENING  = self.hex_to_rgb(col.get("listening",  "#32D270"))
        self.C_SPEAKING   = self.hex_to_rgb(col.get("speaking",   "#FFA532"))
        self.C_PROCESSING = self.hex_to_rgb(col.get("processing", "#A578FF"))
        self.C_IDLE       = self.hex_to_rgb(col.get("idle",       "#828596"))
        self.C_TEXT_WHITE = self.hex_to_rgb(col.get("text_white", "#EBF0FA"))
        self.C_TEXT_GRAY  = self.hex_to_rgb(col.get("text_gray",  "#828596"))
        self.C_ACCENT     = self.hex_to_rgb(col.get("accent",     "#64B4FF"))

    # ── Public render entry point ────────────────────────────────────────────

    def render(self, base_img, voice_state, transcript_text,
               conversation_history=None):
        if conversation_history is None:
            conversation_history = []

        W, H = self.width, self.height
        t = time.time()

        img  = Image.new("RGB", (W, H), self.C_BG)
        draw = ImageDraw.Draw(img)

        CHAT_TOP = self.HEADER_H + 6
        CHAT_BOT = H - self.FOOTER_H - 6

        # ── 1. Header ────────────────────────────────────────────────────────
        draw.rectangle([0, 0, W, self.HEADER_H], fill=self.C_HEADER)
        draw.line([0, self.HEADER_H, W, self.HEADER_H],
                  fill=self.C_DIVIDER, width=1)

        dot_color = self._state_color(voice_state, t)
        dot_x, dot_y = 20, self.HEADER_H // 2
        r = self.DOT_R
        draw.ellipse([dot_x - r, dot_y - r, dot_x + r, dot_y + r],
                     fill=dot_color)

        title_font = self.get_font(self.TITLE_FS)
        draw.text((dot_x + r + 10, self.HEADER_H // 2 - self.TITLE_FS // 2),
                  self.TITLE_TEXT, font=title_font, fill=self.C_TITLE)

        # ── 2. Build bubble list ─────────────────────────────────────────────
        user_font  = self.get_font(self.USER_FS)
        asst_font  = self.get_font(self.ASST_FS)
        MAX_BW     = W - 70

        bubbles = []
        for turn in conversation_history[-self.MAX_TURNS:]:
            user_text  = turn.get("user", "")
            asst_text  = turn.get("assistant", "")
            turn_state = turn.get("state", "done")

            if user_text:
                bubbles.append({
                    "side":  "user",
                    "lines": self._wrap(user_text, user_font,
                                        MAX_BW - self.PAD * 2, draw),
                    "fill":  self.C_USER_BG,
                    "color": self.C_USER_TEXT,
                    "font":  user_font,
                })

            asst_display, asst_col = self._asst_text(turn_state, asst_text, t)
            if asst_display:
                bubbles.append({
                    "side":  "asst",
                    "lines": self._wrap(asst_display, asst_font,
                                        MAX_BW - self.PAD * 2, draw),
                    "fill":  self.C_ASST_BG,
                    "color": asst_col,
                    "font":  asst_font,
                })

        # ── 3. Draw microphone when chat is empty ────────────────────────────
        if not bubbles:
            self._draw_mic(draw, W // 2, (CHAT_TOP + CHAT_BOT) // 2,
                           t, voice_state)

        # ── 4. Paint bubbles (anchor to bottom) ──────────────────────────────
        def bh(b):
            f  = b["font"]
            lh = (f.size if hasattr(f, "size") else self.USER_FS) + self.LINE_GAP
            return len(b["lines"]) * lh + self.PAD * 2

        total_h = (sum(bh(b) + self.BUBBLE_GAP for b in bubbles)
                   - self.BUBBLE_GAP) if bubbles else 0
        cy = max(CHAT_TOP, CHAT_BOT - total_h)

        for b in bubbles:
            f  = b["font"]
            lh = (f.size if hasattr(f, "size") else self.USER_FS) + self.LINE_GAP
            h  = bh(b)
            bw = min(MAX_BW,
                     max((draw.textlength(l, font=f) for l in b["lines"]),
                         default=20) + self.PAD * 2 + 2)
            bx = (W - self.MARGIN - bw) if b["side"] == "user" else self.MARGIN

            if CHAT_TOP <= cy < CHAT_BOT:
                self._bubble(draw, bx, cy, bx + bw, cy + h,
                             r=self.RADIUS, fill=b["fill"])
                for i, line in enumerate(b["lines"]):
                    draw.text((bx + self.PAD, cy + self.PAD + i * lh),
                              line, font=f, fill=b["color"])
            cy += h + self.BUBBLE_GAP

        # ── 5. Footer ────────────────────────────────────────────────────────
        draw.line([0, H - self.FOOTER_H, W, H - self.FOOTER_H],
                  fill=self.C_DIVIDER, width=1)
        draw.rectangle([0, H - self.FOOTER_H, W, H], fill=self.C_HEADER)

        status_label, status_col = self._status_label(voice_state)
        status_font = self.get_font(self.STATUS_FS)
        if status_label:
            draw.text((16, H - self.FOOTER_H + (self.FOOTER_H - self.STATUS_FS) // 2),
                      status_label, font=status_font, fill=status_col)

        if voice_state in ("listening", "speaking"):
            self._draw_wave(draw,
                            W - 60,
                            H - self.FOOTER_H + self.FOOTER_H // 2,
                            t, status_col)

        return img

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _state_color(self, state, t):
        if state == "listening":
            p = (math.sin(t * 3.5) + 1) / 2
            return tuple(int(c * (0.4 + 0.6 * p)) for c in self.C_LISTENING)
        if state == "speaking":
            p = (math.sin(t * 7) + 1) / 2
            return tuple(int(c * (0.4 + 0.6 * p)) for c in self.C_SPEAKING)
        if state == "processing":
            return self.C_PROCESSING
        return self.C_IDLE

    def _asst_text(self, turn_state, asst_text, t):
        if turn_state == "listening":
            return ("...", self.C_TEXT_GRAY)
        if turn_state == "processing":
            dots = "·" * (1 + int(t * 2.5) % 3)
            return (f"思考中 {dots}", self.C_ACCENT)
        if turn_state == "speaking":
            return (asst_text or "正在回答...", self.C_SPEAKING)
        if turn_state == "done":
            return (asst_text or "✓ 已回答", self.C_TEXT_GRAY)
        return ("", self.C_TEXT_GRAY)

    def _status_label(self, state):
        if state == "listening":
            return ("小派听候指示...", self.C_LISTENING)
        if state == "processing":
            return ("正在处理...", self.C_PROCESSING)
        if state == "speaking":
            return ("小派回答中", self.C_SPEAKING)
        return ("", self.C_IDLE)

    def _draw_mic(self, draw, cx, cy, t, state):
        try:
            icon_font = self.get_icon_font(self.MIC_SIZE)
        except Exception:
            return
        icon_char = self.MIC_CHAR
        color, radius = self._state_color(state, t), 52

        if state == "listening":
            p = (math.sin(t * 3.5) + 1) / 2
            radius = int(50 + 12 * p)
        elif state == "speaking":
            p = (math.sin(t * 7) + 1) / 2
            radius = int(50 + 8 * p)

        glow = tuple(c // self.MIC_GLOW_DIV for c in
                     (self.C_LISTENING if state == "listening"
                      else self.C_SPEAKING if state == "speaking"
                      else self.C_PROCESSING))
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     fill=glow)
        try:
            bb = icon_font.getbbox(icon_char)
            iw, ih = bb[2] - bb[0], bb[3] - bb[1]
        except Exception:
            iw, ih = self.MIC_SIZE, self.MIC_SIZE
        draw.text((cx - iw // 2, cy - ih // 2),
                  icon_char, font=icon_font, fill=color)

    def _wrap(self, text, font, max_w, draw):
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=font) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines or [text]

    def _bubble(self, draw, x1, y1, x2, y2, r, fill):
        draw.rectangle([x1 + r, y1, x2 - r, y2], fill=fill)
        draw.rectangle([x1, y1 + r, x2, y2 - r], fill=fill)
        for cx, cy in [(x1, y1), (x2 - 2*r, y1),
                       (x1, y2 - 2*r), (x2 - 2*r, y2 - 2*r)]:
            draw.ellipse([cx, cy, cx + 2*r, cy + 2*r], fill=fill)

    def _draw_wave(self, draw, cx, cy, t, color):
        bw, gap = 4, 5
        for i in range(5):
            h = int(6 + 14 * abs(math.sin(t * 3.5 + i * 1.1)))
            bx = cx + i * (bw + gap)
            draw.rectangle([bx, cy - h // 2, bx + bw, cy + h // 2],
                           fill=color)
