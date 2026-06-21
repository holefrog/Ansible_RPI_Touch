#!/usr/bin/env python
# ui_screen_assistant.py - Voice Assistant Chat Interface

import time
import math
from PIL import Image, ImageDraw, ImageFont
from ui_core import BaseUIRenderer

# ── Color Palette ────────────────────────────────────────────────────────────
BG          = (8,  10,  18)        # main background
HEADER_BG   = (16, 20,  36)        # header / footer strip
DIVIDER     = (35, 45,  65)        # 1-px separator lines
USER_BUBBLE = (40, 90,  195)       # blue - user speech bubble
ASST_BUBBLE = (26, 32,  50)        # dark - assistant bubble
TEXT_WHITE  = (235, 240, 250)
TEXT_GRAY   = (130, 145, 170)
ACCENT      = (100, 180, 255)      # blue accent (processing)
GREEN       = (50,  210, 110)      # listening indicator
ORANGE      = (255, 165,  50)      # speaking indicator
PURPLE      = (165, 120, 255)      # processing indicator


class AssistantScreenRenderer(BaseUIRenderer):
    """
    Full-screen voice assistant chat interface.
    Renders a scrollable-style conversation bubble list plus a status footer.
    """

    # ── Public render entry point ────────────────────────────────────────────

    def render(self, base_img, voice_state, transcript_text,
               conversation_history=None):
        """
        Args:
            base_img:             The base image (ignored – we draw a full bg).
            voice_state:          "listening" | "processing" | "speaking" | "idle"
            transcript_text:      Current in-flight transcript (may be empty).
            conversation_history: List[dict] from UIManager.
        """
        if conversation_history is None:
            conversation_history = []

        W, H = self.width, self.height
        t = time.time()

        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        HEADER_H = 46
        FOOTER_H = 44
        CHAT_TOP = HEADER_H + 6
        CHAT_BOT = H - FOOTER_H - 6

        # ── 1. Header ────────────────────────────────────────────────────────
        draw.rectangle([0, 0, W, HEADER_H], fill=HEADER_BG)
        draw.line([0, HEADER_H, W, HEADER_H], fill=DIVIDER, width=1)

        # Animated status dot
        dot_r = 6
        dot_x, dot_y = 20, HEADER_H // 2
        dot_color = self._state_color(voice_state, t)
        draw.ellipse([dot_x - dot_r, dot_y - dot_r,
                      dot_x + dot_r, dot_y + dot_r], fill=dot_color)

        title_font = self.get_font(17)
        draw.text((36, HEADER_H // 2 - 9), "Voice Assistant",
                  font=title_font, fill=TEXT_WHITE)

        # ── 2. Chat bubbles ──────────────────────────────────────────────────
        MARGIN   = 12
        PAD      = 9
        MAX_BW   = W - 70          # max bubble width
        LINE_H   = 22

        font       = self.get_font(16)
        small_font = self.get_font(14)

        # Collect all rendered bubbles as (is_user, lines, color, text_color)
        # then paint bottom-up so newest is always at the bottom.
        bubbles = []
        for turn in conversation_history:
            user_text  = turn.get("user", "")
            asst_text  = turn.get("assistant", "")
            turn_state = turn.get("state", "done")

            if user_text:
                bubbles.append({
                    "side": "user",
                    "lines": self._wrap(user_text, font, MAX_BW - PAD * 2, draw),
                    "fill":  USER_BUBBLE,
                    "color": TEXT_WHITE,
                })

            asst_display, asst_col = self._asst_text(turn_state, asst_text, t)
            if asst_display:
                bubbles.append({
                    "side": "asst",
                    "lines": self._wrap(asst_display, small_font,
                                        MAX_BW - PAD * 2, draw),
                    "fill":  ASST_BUBBLE,
                    "color": asst_col,
                    "font":  small_font,
                })

        # Measure total height, then paint from bottom
        def bubble_h(b):
            f = b.get("font", font)
            lh = f.size + 6 if hasattr(f, "size") else LINE_H
            return len(b["lines"]) * lh + PAD * 2

        total_h = sum(bubble_h(b) + 8 for b in bubbles) - 8 if bubbles else 0

        cy = CHAT_BOT - total_h  # start Y; may be negative → clip naturally
        if cy < CHAT_TOP:
            cy = CHAT_TOP        # clamp to top

        for b in bubbles:
            f  = b.get("font", font)
            lh = f.size + 6 if hasattr(f, "size") else LINE_H
            bh = len(b["lines"]) * lh + PAD * 2
            bw = min(MAX_BW, max(
                (draw.textlength(l, font=f) for l in b["lines"]),
                default=20
            ) + PAD * 2 + 2)

            if b["side"] == "user":
                bx = W - MARGIN - bw
            else:
                bx = MARGIN

            by = cy
            if by + bh > CHAT_BOT:   # clip if overflows
                pass
            if by >= CHAT_TOP:
                self._bubble(draw, bx, by, bx + bw, by + bh, r=11, fill=b["fill"])
                for i, line in enumerate(b["lines"]):
                    draw.text((bx + PAD, by + PAD + i * lh),
                              line, font=f, fill=b["color"])

            cy += bh + 8

        # ── 3. Footer / status bar ───────────────────────────────────────────
        draw.line([0, H - FOOTER_H, W, H - FOOTER_H], fill=DIVIDER, width=1)
        draw.rectangle([0, H - FOOTER_H, W, H], fill=HEADER_BG)

        status_label, status_col = self._status_label(voice_state)
        if status_label:
            draw.text((16, H - FOOTER_H + 13),
                      status_label, font=small_font, fill=status_col)

        # Animated sound-wave bars on the right
        if voice_state in ("listening", "speaking"):
            self._draw_wave(draw, W - 60, H - FOOTER_H + FOOTER_H // 2,
                            t, status_col)

        return img

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _state_color(self, state, t):
        """Returns an (optionally pulsed) color for the header dot."""
        if state == "listening":
            pulse = (math.sin(t * 4) + 1) / 2
            return tuple(int(c * (0.45 + 0.55 * pulse)) for c in GREEN)
        if state == "speaking":
            pulse = (math.sin(t * 8) + 1) / 2
            return tuple(int(c * (0.45 + 0.55 * pulse)) for c in ORANGE)
        if state == "processing":
            return PURPLE
        return TEXT_GRAY

    def _asst_text(self, turn_state, asst_text, t):
        """Returns (display_text, color) for the assistant bubble."""
        if turn_state == "listening":
            return ("...", TEXT_GRAY)
        if turn_state == "processing":
            dots = "·" * (1 + int(t * 2.5) % 3)
            return (f"思考中 {dots}", ACCENT)
        if turn_state == "speaking":
            return (asst_text or "正在回答...", ORANGE)
        if turn_state == "done":
            return (asst_text or "✓ 已回答", TEXT_GRAY)
        return ("", TEXT_GRAY)

    def _status_label(self, state):
        """Returns (label, color) for the footer."""
        if state == "listening":
            return ("小派听候指示...", GREEN)
        if state == "processing":
            return ("正在处理...", PURPLE)
        if state == "speaking":
            return ("小派回答中", ORANGE)
        return ("", TEXT_GRAY)

    def _wrap(self, text, font, max_w, draw):
        """Word-wrap text into lines that fit max_w."""
        words  = text.split()
        lines  = []
        cur    = ""
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
        """Draw a pill-shaped (rounded rect) chat bubble."""
        draw.rectangle([x1 + r, y1, x2 - r, y2], fill=fill)
        draw.rectangle([x1, y1 + r, x2, y2 - r], fill=fill)
        for cx, cy in [(x1, y1), (x2 - 2*r, y1),
                       (x1, y2 - 2*r), (x2 - 2*r, y2 - 2*r)]:
            draw.ellipse([cx, cy, cx + 2*r, cy + 2*r], fill=fill)

    def _draw_wave(self, draw, cx, cy, t, color):
        """Five animated vertical bars that simulate a sound waveform."""
        bar_w, gap = 4, 5
        for i in range(5):
            h = int(6 + 14 * abs(math.sin(t * 3.5 + i * 1.1)))
            bx = cx + i * (bar_w + gap)
            draw.rectangle([bx, cy - h // 2, bx + bar_w, cy + h // 2],
                           fill=color)
