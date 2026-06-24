import time
import subprocess
import logging
import os
from PIL import Image, ImageDraw

logger = logging.getLogger("BootAnimation")

def cubic_ease_in(t):
    """
    Cubic ease-in function
    :param t: progress between 0.0 and 1.0
    :return: value between 0.0 and 1.0
    """
    return t * t * t

def play_boot_animation(display_ctx, config):
    """
    Play the Terminator reboot animation before the UI starts.
    """
    if not config or not config.get("enabled", False):
        return

    logger.info("Starting Terminator boot animation...")
    
    duration_ms = config.get("duration_ms", 2000)
    eye_color = tuple(config.get("eye_color", [255, 30, 30]))
    max_radius = config.get("max_radius", 80)
    audio_file = config.get("audio_file", "./boot.wav")

    # The audio_file path is relative to the touchscreen scripts.
    # We should ensure absolute path if possible.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(audio_file):
        audio_file = os.path.join(base_dir, audio_file)

    # Start audio playback asynchronously
    try:
        if os.path.exists(audio_file):
            # Using paplay for PipeWire
            subprocess.Popen(["paplay", audio_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            logger.warning(f"Boot audio file not found: {audio_file}")
    except Exception as e:
        logger.error(f"Failed to play boot audio: {e}")

    # Display loop
    device = display_ctx["device"]
    width = display_ctx["width"]
    height = display_ctx["height"]
    center = (width // 2, height // 2)

    # Immediately flush a black screen to fix the white bar
    device.show_image(Image.new("RGB", (width, height), (0, 0, 0)))

    start_time = time.monotonic()
    end_time = start_time + (duration_ms / 1000.0)

    # Pre-calculate target color for glow
    r, g, b = eye_color

    while True:
        now = time.monotonic()
        if now >= end_time:
            break

        progress = (now - start_time) / (duration_ms / 1000.0)
        progress = max(0.0, min(1.0, progress))
        
        # Apply easing function for dramatic effect
        eased_progress = cubic_ease_in(progress)
        
        # Calculate current radius
        current_radius = max(1, int(max_radius * eased_progress))

        # Create a black background
        # We use RGBA to allow drawing alpha-blended glow layers easily
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img, "RGBA")

        # Draw glowing layers (from outer faint to inner solid)
        glow_layers = 5
        for i in range(glow_layers, -1, -1):
            if current_radius <= 1 and i > 0:
                continue
                
            # Outer layers are larger and more transparent
            # Inner layer (i=0) is exact size and opaque
            layer_radius = current_radius + (i * 4)
            
            # Alpha fades out for outer layers
            if i == 0:
                alpha = 255
            else:
                alpha = int(255 * (0.5 ** i))
                
            color_with_alpha = (r, g, b, alpha)
            
            bbox = [
                center[0] - layer_radius,
                center[1] - layer_radius,
                center[0] + layer_radius,
                center[1] + layer_radius
            ]
            draw.ellipse(bbox, fill=color_with_alpha)

        # Send frame to SPI display
        device.show_image(img)

        # Prevent 100% CPU pinning
        time.sleep(0.01)

    # Ensure it finishes with a fully drawn eye
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    draw.ellipse([center[0] - max_radius, center[1] - max_radius, center[0] + max_radius, center[1] + max_radius], fill=(r, g, b, 255))
    device.show_image(img)
    
    # Hold for a tiny fraction just to show the final state
    time.sleep(0.1)
    logger.info("Boot animation finished.")
