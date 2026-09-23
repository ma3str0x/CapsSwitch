import os
import sys
import re
import ctypes
import threading

winmm = ctypes.windll.winmm
_lock = threading.Lock()
_counter = 0

def get_sfx_dir():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, 'sfx')
        if os.path.isdir(p):
            return p
    if getattr(sys, 'frozen', False):
        p = os.path.join(os.path.dirname(sys.executable), 'sfx')
        if os.path.isdir(p):
            return p
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'sfx')

def get_available_presets():
    sfx_dir = get_sfx_dir()
    if not os.path.isdir(sfx_dir):
        return {"Main": {"on": "main_sound_on.mp3", "off": "main_sound_off.mp3"}}
    
    presets = {}
    try:
        files = os.listdir(sfx_dir)
        for f in files:
            m = re.match(r'^(.*?)(_on|_off)\.(mp3|wav|ogg)$', f, re.IGNORECASE)
            if m:
                base, kind, ext = m.groups()
                kind = kind.lower().strip('_')
                if base.lower() == 'main_sound':
                    display_name = 'Main'
                else:
                    num_match = re.search(r'\d+', base)
                    if num_match:
                        display_name = f'Preset {int(num_match.group())}'
                    else:
                        display_name = base.replace('_', ' ').title()
                
                if display_name not in presets:
                    presets[display_name] = {}
                presets[display_name][kind] = f
    except Exception as e:
        print(f"Error scanning presets: {e}")
        
    if not presets:
        return {"Main": {"on": "main_sound_on.mp3", "off": "main_sound_off.mp3"}}
        
    ordered = {}
    if 'Main' in presets:
        ordered['Main'] = presets['Main']
    
    other_keys = [k for k in presets.keys() if k != 'Main']
    def sort_key(k):
        m = re.search(r'\d+', k)
        return int(m.group()) if m else 999
    other_keys.sort(key=sort_key)
    
    for k in other_keys:
        ordered[k] = presets[k]
        
    return ordered

def get_preset_names():
    presets = get_available_presets()
    return list(presets.keys())

def play_sound_file(sound_file, volume=70):
    def _worker():
        global _counter
        with _lock:
            _counter = (_counter + 1) % 1000
            alias = f'cs_sfx_{_counter}'
            
        sfx_dir = get_sfx_dir()
        full_path = os.path.join(sfx_dir, sound_file)
        if not os.path.exists(full_path):
            return
            
        vol_mci = max(0, min(1000, int(volume * 10)))
        
        try:
            winmm.mciSendStringW(f'close {alias}', None, 0, None)
            res = winmm.mciSendStringW(f'open "{full_path}" type mpegvideo alias {alias}', None, 0, None)
            if res == 0:
                winmm.mciSendStringW(f'setaudio {alias} volume to {vol_mci}', None, 0, None)
                winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
                winmm.mciSendStringW(f'close {alias}', None, 0, None)
        except Exception as e:
            print(f'Sound play error: {e}')

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def play_preset_sound(preset_name, is_on: bool, volume=70):
    presets = get_available_presets()
    preset = presets.get(preset_name)
    if not preset and "Main" in presets:
        preset = presets["Main"]
    if not preset:
        return
        
    target_key = "on" if is_on else "off"
    sound_file = preset.get(target_key)
    if not sound_file:
        sound_file = preset.get("on") or preset.get("off")
    if sound_file:
        play_sound_file(sound_file, volume)
