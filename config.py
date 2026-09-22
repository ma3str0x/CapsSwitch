import os
import sys
import json
import winreg

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(APP_DIR, "config.json")
RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "CapsSwitch"

DEFAULT_CONFIG = {
    "trigger_key": "Caps Lock",
    "switch_shortcut": "Win+Space",
    "hold_threshold_ms": 220,
    "enable_shift_caps": True,
    "start_with_windows": False,
    "enabled": True
}

def load_config():
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception as e:
            print(f"Config load error: {e}")
    else:
        save_config(config)
    
    config["start_with_windows"] = is_startup_enabled()
    return config

_cached_config = None
_cached_mtime = 0

def get_live_config():
    global _cached_config, _cached_mtime
    try:
        if os.path.exists(CONFIG_FILE):
            mtime = os.path.getmtime(CONFIG_FILE)
            if _cached_config is None or mtime > _cached_mtime:
                _cached_config = load_config()
                _cached_mtime = mtime
    except Exception:
        pass
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Config save error: {e}")

def is_startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

def set_startup_enabled(enable: bool):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                if getattr(sys, 'frozen', False):
                    cmd = f'"{sys.executable}"'
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    vbs_path = os.path.join(base_dir, "CapsSwitch.vbs")
                if os.path.exists(vbs_path):
                    cmd = f'wscript.exe "{vbs_path}"'
                else:
                    pythonw = os.path.join(sys.prefix, "pythonw.exe")
                    if not os.path.exists(pythonw):
                        pythonw = sys.executable
                    main_py = os.path.join(base_dir, "main.py")
                    cmd = f'"{pythonw}" "{main_py}"'
                
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            return True
    except Exception as e:
        print(f"Startup config error: {e}")
        return False
