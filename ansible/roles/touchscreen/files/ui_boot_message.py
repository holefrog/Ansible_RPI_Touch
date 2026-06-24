import sys
from PIL import Image, ImageDraw, ImageFont

def show_network_wait_message(display_ctx, cfg, logger):
    """
    Shows the network wait message on the screen according to ui_config.toml.
    Exits the application if necessary configuration is missing or invalid.
    """
    device = display_ctx["device"]
    w = display_ctx["width"]
    h = display_ctx["height"]
    
    if "ui" not in cfg or "boot_animation" not in cfg["ui"] or "global" not in cfg["ui"]:
        logger.error("Missing ui config. Exiting.")
        sys.exit(1)

    boot_cfg = cfg["ui"]["boot_animation"]
    global_cfg = cfg["ui"]["global"]
    
    if "network_wait_text1" not in boot_cfg or "network_wait_text3" not in boot_cfg or "font_main" not in global_cfg:
        logger.error("Missing necessary ui config items. Exiting.")
        sys.exit(1)

    if "network_wait_color" not in boot_cfg:
        logger.error("Missing network_wait_color. Exiting.")
        sys.exit(1)

    t1_cfg = boot_cfg["network_wait_text1"]
    t3_cfg = boot_cfg["network_wait_text3"]
    
    if not isinstance(t1_cfg, dict) or not isinstance(t3_cfg, dict):
        logger.error("network_wait_text1 and 3 must be dictionaries. Exiting.")
        sys.exit(1)
        
    if "text" not in t1_cfg or "font_size" not in t1_cfg or "text" not in t3_cfg or "font_size" not in t3_cfg:
        logger.error("Missing text or font_size in network_wait text configs. Exiting.")
        sys.exit(1)

    wait_text1 = t1_cfg["text"]
    wait_text3 = t3_cfg["text"]
    
    size1 = t1_cfg["font_size"]
    size3 = t3_cfg["font_size"]
    
    pos1 = t1_cfg.get("pos")
    pos3 = t3_cfg.get("pos")
    if not pos1 or not pos3:
        logger.error("Missing pos in network_wait text configs. Exiting.")
        sys.exit(1)

    wait_color = tuple(boot_cfg["network_wait_color"])
    font_path = global_cfg["font_main"]

    try:
        font1 = ImageFont.truetype(font_path, size1)
        font3 = ImageFont.truetype(font_path, size3)
    except Exception as e:
        logger.error(f"Failed to load fonts from {font_path}: {e}")
        sys.exit(1)

    wait_img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(wait_img)

    draw.text(tuple(pos1), wait_text1, font=font1, fill=wait_color)
    draw.text(tuple(pos3), wait_text3, font=font3, fill=wait_color)

    device.show_image(wait_img)
