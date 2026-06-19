#!/usr/bin/env python
import os
import logging

# Fallback parser if tomllib is not available
try:
    import tomllib
except ModuleNotFoundError:
    # Attempt to fallback to `toml` package if installed
    try:
        import toml as tomllib
    except ModuleNotFoundError:
        logging.error("No toml parsing library found. Please install `toml` or use Python 3.11+")
        raise

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_CONFIG_FILE = os.path.join(BASE_DIR, "ui_config.toml")

def load_ui_config():
    """
    加载并解析 ui_config.toml
    """
    if not os.path.exists(UI_CONFIG_FILE):
        logging.error(f"未找到 UI 配置文件: {UI_CONFIG_FILE}")
        return {}

    try:
        with open(UI_CONFIG_FILE, "rb") as f:
            if hasattr(tomllib, "load"):
                config = tomllib.load(f)
            else:
                # Fallback for old `toml` library which reads string
                f.close()
                with open(UI_CONFIG_FILE, "r") as fs:
                    config = tomllib.load(fs)
        
        logging.info("成功加载 UI 配置文件 ui_config.toml")
        return config
    except Exception as e:
        logging.error(f"解析 UI 配置文件失败: {e}")
        return {}
