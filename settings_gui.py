import os
import sys
import threading
import ctypes
from ctypes import wintypes
import customtkinter as ctk

C_BG = ("#fffefb", "#211f1d")
C_WIDGET_BG = ("#ffffff", "#2b2826")
C_MAIN_FG = ("#2b2724", "#e8e3dc")
C_LABEL = ("#3b3632", "#d4cec9")
C_TITLE = ("#24211e", "#ffffff")
C_CHECKBOX_TEXT = ("#36322e", "#d4cec9")
C_MAIN_HOVER = ("#1a1715", "#c8c1b9")
C_MUTED = ("#5c554e", "#a69f98")
C_HELPER = ("#888078", "#9e968d")
C_ACCENT = ("#825633", "#c69d7a")
C_LIGHT_HOVER = ("#f0ebe0", "#3d3935")
C_BORDER = ("#ece6dc", "#4a4540")
C_CHECKBOX_BORDER = ("#d8d2c7", "#5c5650")
C_SCROLL_BG = ("#fcfbfa", "#262321")
C_DANGER_HOVER = ("#feebe8", "#593333")
C_DANGER = ("#c94a4a", "#e86464")
C_ERROR = ("#b83232", "#eb5b5b")
C_CHECKMARK = ("#ffffff", "#1f1c1a")

from config import load_config, save_config, set_startup_enabled
from sound_player import get_preset_names, play_preset_sound

user32 = ctypes.windll.user32
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

_window_open = False
_window_lock = threading.Lock()

KEY_OPTIONS = [
    "Caps Lock",
    "Tilde (~)"
]
CUSTOM_KEY_LABEL = "Custom key..."

COMBO_OPTIONS = [
    "Alt+Shift",
    "Win+Space",
    "Ctrl+Shift"
]

VK_NAMES = {
    0x14: "Caps Lock",
    0xC0: "Tilde (~)",
    0xA3: "Right Ctrl",
    0xA5: "Right Alt",
    0x91: "Scroll Lock",
    0x13: "Pause / Break",
    0x2D: "Insert",
    0x24: "Home",
    0x23: "End",
    0x21: "Page Up",
    0x22: "Page Down",
    0x5D: "Menu (Apps)",
    0x70: "F1",
    0x71: "F2",
    0x72: "F3",
    0x73: "F4",
    0x74: "F5",
    0x75: "F6",
    0x76: "F7",
    0x77: "F8",
    0x78: "F9",
    0x79: "F10",
    0x7A: "F11",
    0x7B: "F12",
}

KEYSYM_TO_VK = {
    "Caps_Lock": 0x14,
    "asciitilde": 0xC0,
    "grave": 0xC0,
    "Control_R": 0xA3,
    "Alt_R": 0xA5,
    "Scroll_Lock": 0x91,
    "Pause": 0x13,
    "Break": 0x13,
    "Insert": 0x2D,
    "Home": 0x24,
    "End": 0x23,
    "Prior": 0x21,
    "Next": 0x22,
    "Menu": 0x5D,
    "App": 0x5D,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}

DISALLOWED_VKS = {
    0x0D: "Enter",
    0x5B: "Left Windows",
    0x5C: "Right Windows",
    0x1B: "Escape",
}

def vk_to_name(vk):
    if vk in VK_NAMES:
        return VK_NAMES[vk]
    if 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x30 <= vk <= 0x39:
        return chr(vk)
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x70 + 1}"
    if 0x60 <= vk <= 0x69:
        return f"Numpad {vk - 0x60}"
    return f"Key (0x{vk:02X})"

def name_to_vk(name):
    for vk, n in VK_NAMES.items():
        if n == name:
            return vk
    for sym, vk in KEYSYM_TO_VK.items():
        if sym == name:
            return vk
    return None

def get_running_apps():
    import subprocess
    import ctypes
    from ctypes import wintypes
    

    
    apps = set()
    try:
        # 1. Get all running PIDs to exe names quickly using tasklist
        pid_to_name = {}
        output = subprocess.check_output('tasklist /FO CSV /NH', shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in output.strip().split('\n'):
            if line:
                parts = line.split('","')
                if len(parts) >= 2:
                    name = parts[0].strip('"').lower()
                    pid_str = parts[1].strip('"')
                    if pid_str.isdigit():
                        pid_to_name[int(pid_str)] = name

        # 2. Filter using EnumWindows to get only visible apps (avoids OpenProcess hangs)
        user32 = ctypes.windll.user32
        def enum_windows_proc(hwnd, lParam):
            if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pid_to_name:
                    basename = pid_to_name[pid.value]
                    if basename.endswith('.exe') and basename not in ("applicationframehost.exe", "textinputhost.exe", "shellexperiencehost.exe", "systemsettings.exe", "explorer.exe", "svchost.exe", "conhost.exe"):
                        apps.add(basename)
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(enum_windows_proc), 0)
    except Exception:
        pass
        
    return sorted(list(apps))

class SettingsWindow(ctk.CTk):
    def __init__(self, config, on_save_callback=None):
        super().__init__()
        
        self.config = config
        self.on_save_callback = on_save_callback
        
        self.title("CapsSwitch")
        self.resizable(False, False)
        
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('capsswitch.settings.ui.1')
        except Exception:
            pass


        def _find_asset(rel_path):
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                p = os.path.join(sys._MEIPASS, rel_path)
                if os.path.exists(p):
                    return p
            if getattr(sys, 'frozen', False):
                p = os.path.join(os.path.dirname(sys.executable), rel_path)
                if os.path.exists(p):
                    return p
            base_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_dir, rel_path)

        icon_ico_path = _find_asset(os.path.join("img", "logo_base.ico"))
        icon_png_path = _find_asset(os.path.join("img", "logo_base.png"))
        
        if os.path.exists(icon_ico_path):
            try:
                self.iconbitmap(icon_ico_path)
            except Exception:
                pass
                
        if os.path.exists(icon_png_path):
            try:
                from PIL import Image, ImageTk
                self._app_icon_photo = ImageTk.PhotoImage(Image.open(icon_png_path))
                self.iconphoto(True, self._app_icon_photo)
            except Exception:
                pass
        
        
        ctk.set_appearance_mode(self.config.get("theme", "System"))
        self.configure(fg_color=C_BG)
        
        # Outer frame
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(padx=20, pady=(14, 14), fill="both", expand=True)

        # 1. Pinned bottom buttons (ALWAYS visible at the bottom)
        self.btn_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.btn_frame.pack(side="bottom", fill="x")
        
        self.save_btn = ctk.CTkButton(self.btn_frame, text="Save", command=self.save_settings,
                                      fg_color=C_MAIN_FG, hover_color=C_MAIN_HOVER, text_color=C_WIDGET_BG, width=75, height=28)
        self.save_btn.pack(side="right", padx=(8, 0))
        
        self.cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", command=self.close_window,
                                        fg_color="transparent", hover_color=C_LIGHT_HOVER, text_color=C_MUTED, width=75, height=28)
        self.cancel_btn.pack(side="right")

        self.sep = ctk.CTkFrame(self.main_container, height=1, fg_color=C_BORDER)
        self.sep.pack(side="bottom", fill="x", pady=(6, 8))

        # 2. Scrollable/Expandable content frame sitting above buttons
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(side="top", fill="both", expand=True)

        self.title_label = ctk.CTkLabel(self.content_frame, text="Settings", 
                                        font=ctk.CTkFont(size=17, weight="bold"), text_color=C_TITLE)
        self.title_label.pack(pady=(0, 6), anchor="w")
        
        # Switch language key
        self.key_label = ctk.CTkLabel(self.content_frame, text="Switch language key:", 
                                      font=ctk.CTkFont(size=12), text_color=C_LABEL)
        self.key_label.pack(anchor="w")
        
        self.key_row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.key_row_frame.pack(pady=(2, 1), fill="x")
        
        self._selected_vk = self.config.get("trigger_vk", 0x14)
        saved_name = self.config.get("trigger_key", "Caps Lock")
        if self._selected_vk in VK_NAMES:
            self._selected_key_name = VK_NAMES[self._selected_vk]
        else:
            self._selected_key_name = saved_name
        self._listening_for_key = False
        
        current_key = self._selected_key_name
        dropdown_values = list(KEY_OPTIONS)
        if current_key not in dropdown_values:
            dropdown_values.append(current_key)
        dropdown_values.append(CUSTOM_KEY_LABEL)
        
        self.key_var = ctk.StringVar(value=current_key)
        self.key_dropdown = ctk.CTkOptionMenu(self.key_row_frame, values=dropdown_values,
                                              variable=self.key_var,
                                              command=self._on_key_selected,
                                              fg_color=C_WIDGET_BG, text_color=C_MAIN_FG, 
                                              button_color=C_WIDGET_BG, button_hover_color=C_LIGHT_HOVER,
                                              dropdown_fg_color=C_WIDGET_BG, dropdown_text_color=C_MAIN_FG,
                                              height=28)
        self.key_dropdown.pack(side="left", fill="x", expand=True)
        
        self.delete_key_btn = ctk.CTkButton(self.key_row_frame, text="✕", width=28, height=28,
                                            fg_color=C_WIDGET_BG, hover_color=C_DANGER_HOVER,
                                            text_color=C_DANGER, font=ctk.CTkFont(size=12, weight="bold"),
                                            command=self.delete_custom_key)
        
        self.key_status_label = ctk.CTkLabel(self.content_frame, text="", 
                                             font=ctk.CTkFont(size=11), text_color=C_HELPER)
        self.key_status_label.pack(anchor="w", pady=(0, 2))
        self._update_delete_button_visibility()
        
        # Windows combo
        self.combo_label = ctk.CTkLabel(self.content_frame, text="Windows system combination:", 
                                        font=ctk.CTkFont(size=12), text_color=C_LABEL)
        self.combo_label.pack(anchor="w")
        
        self.combo_var = ctk.StringVar(value=self.config.get("switch_shortcut", "Alt+Shift"))
        self.combo_dropdown = ctk.CTkOptionMenu(self.content_frame, values=COMBO_OPTIONS, variable=self.combo_var,
                                                fg_color=C_WIDGET_BG, text_color=C_MAIN_FG, 
                                                button_color=C_WIDGET_BG, button_hover_color=C_LIGHT_HOVER,
                                                dropdown_fg_color=C_WIDGET_BG, dropdown_text_color=C_MAIN_FG,
                                                height=28)
        self.combo_dropdown.pack(pady=(2, 6), fill="x")
        
        # PTT slider
        self.ptt_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.ptt_frame.pack(fill="x", pady=(0, 1))
        
        self.ptt_label = ctk.CTkLabel(self.ptt_frame, text="Push-to-Talk delay:", 
                                      font=ctk.CTkFont(size=12), text_color=C_LABEL)
        self.ptt_label.pack(side="left")
        
        self.ptt_value_label = ctk.CTkLabel(self.ptt_frame, text=f"{self.config.get('hold_threshold_ms', 220)} ms", 
                                            font=ctk.CTkFont(size=12, weight="bold"), text_color=C_ACCENT)
        self.ptt_value_label.pack(side="right")
        
        self.ptt_var = ctk.IntVar(value=self.config.get("hold_threshold_ms", 220))
        self.ptt_slider = ctk.CTkSlider(self.content_frame, from_=100, to=500, number_of_steps=40,
                                        variable=self.ptt_var, command=self.update_ptt_label,
                                        button_color=C_MAIN_FG, button_hover_color=C_MAIN_HOVER,
                                        height=16)
        self.ptt_slider.pack(fill="x", pady=(2, 6))
        
        # Checkboxes: Shift+Caps & Auto start
        self.shift_caps_var = ctk.BooleanVar(value=self.config.get("enable_shift_caps", True))
        self.shift_caps_check = ctk.CTkCheckBox(self.content_frame, text="Shift + Caps Lock switches UPPERCASE",
                                                variable=self.shift_caps_var,
                                                text_color=C_CHECKBOX_TEXT, fg_color=C_MAIN_FG, hover_color=C_MAIN_HOVER,
                                                border_color=C_CHECKBOX_BORDER, checkmark_color=C_CHECKMARK, checkbox_width=18, checkbox_height=18)
        self.shift_caps_check.pack(pady=(0, 4), anchor="w")
        
        self.auto_start_var = ctk.BooleanVar(value=self.config.get("start_with_windows", False))
        self.auto_start_check = ctk.CTkCheckBox(self.content_frame, text="Start automatically with Windows",
                                                variable=self.auto_start_var,
                                                text_color=C_CHECKBOX_TEXT, fg_color=C_MAIN_FG, hover_color=C_MAIN_HOVER,
                                                border_color=C_CHECKBOX_BORDER, checkmark_color=C_CHECKMARK, checkbox_width=18, checkbox_height=18)
        self.auto_start_check.pack(pady=(0, 5), anchor="w")
        
        # 5. Pause / resume hotkey section (NO presets, only custom bind)
        self.pause_hotkey_var = ctk.BooleanVar(value=self.config.get("pause_hotkey_enabled", False))
        self.pause_hotkey_check = ctk.CTkCheckBox(self.content_frame, text="Pause / resume hotkey",
                                                  variable=self.pause_hotkey_var,
                                                  command=self._toggle_pause_hotkey_visibility,
                                                  text_color=C_CHECKBOX_TEXT, fg_color=C_MAIN_FG, hover_color=C_MAIN_HOVER,
                                                  border_color=C_CHECKBOX_BORDER, checkmark_color=C_CHECKMARK, checkbox_width=18, checkbox_height=18)
        self.pause_hotkey_check.pack(pady=(0, 4), anchor="w")
        
        self.pause_hotkey_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self._selected_pause_vk = self.config.get("pause_hotkey_vk", None)
        saved_pause_name = self.config.get("pause_hotkey_key", "None")
        if self._selected_pause_vk in VK_NAMES:
            self._selected_pause_key_name = VK_NAMES[self._selected_pause_vk]
        else:
            self._selected_pause_key_name = saved_pause_name
        self._listening_for_pause_key = False
        
        self.pause_row_frame = ctk.CTkFrame(self.pause_hotkey_frame, fg_color="transparent")
        self.pause_row_frame.pack(fill="x")
        
        button_display_text = self._selected_pause_key_name if (self._selected_pause_key_name and self._selected_pause_key_name != "None") else "Click to set key"
        self.pause_key_btn = ctk.CTkButton(self.pause_row_frame, text=button_display_text,
                                           command=self._start_pause_key_binding,
                                           fg_color=C_WIDGET_BG, hover_color=C_LIGHT_HOVER,
                                           text_color=C_MAIN_FG, height=28)
        self.pause_key_btn.pack(side="left", fill="x", expand=True)
        
        self.delete_pause_key_btn = ctk.CTkButton(self.pause_row_frame, text="✕", width=28, height=28,
                                                  fg_color=C_WIDGET_BG, hover_color=C_DANGER_HOVER,
                                                  text_color=C_DANGER, font=ctk.CTkFont(size=12, weight="bold"),
                                                  command=self.delete_pause_key)
        
        self.pause_key_status_label = ctk.CTkLabel(self.pause_hotkey_frame, text="", 
                                                   font=ctk.CTkFont(size=11), text_color=C_HELPER)
        self.pause_key_status_label.pack(anchor="w", pady=(1, 2))
        self._update_pause_delete_button_visibility()
        
        # 6. Sound signal section
        self.sound_var = ctk.BooleanVar(value=self.config.get("sound_enabled", False))
        self.sound_check = ctk.CTkCheckBox(self.content_frame, text="Sound signal on pause / resume",
                                           variable=self.sound_var,
                                           command=self._toggle_sound_visibility,
                                           text_color=C_CHECKBOX_TEXT, fg_color=C_MAIN_FG, hover_color=C_MAIN_HOVER,
                                           border_color=C_CHECKBOX_BORDER, checkmark_color=C_CHECKMARK, checkbox_width=18, checkbox_height=18)
        self.sound_check.pack(pady=(0, 4), anchor="w")
        
        self.sound_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        
        # Sound select row
        self.sound_row = ctk.CTkFrame(self.sound_frame, fg_color="transparent")
        self.sound_row.pack(fill="x", pady=(0, 3))
        
        available_presets = get_preset_names()
        saved_preset = self.config.get("sound_preset", "Main")
        if saved_preset not in available_presets and available_presets:
            available_presets.append(saved_preset)
        if not saved_preset and available_presets:
            saved_preset = available_presets[0]
            
        self.sound_var_choice = ctk.StringVar(value=saved_preset)
        self.sound_dropdown = ctk.CTkOptionMenu(self.sound_row, values=available_presets,
                                               variable=self.sound_var_choice,
                                               command=self._on_preset_selected,
                                               fg_color=C_WIDGET_BG, text_color=C_MAIN_FG,
                                               button_color=C_WIDGET_BG, button_hover_color=C_LIGHT_HOVER,
                                               dropdown_fg_color=C_WIDGET_BG, dropdown_text_color=C_MAIN_FG,
                                               height=28)
        self.sound_dropdown.pack(side="left", fill="x", expand=True)
        
        self.preview_on_btn = ctk.CTkButton(self.sound_row, text="▶ On", width=42, height=28,
                                            fg_color=C_WIDGET_BG, hover_color=C_LIGHT_HOVER,
                                            text_color=C_MAIN_FG, font=ctk.CTkFont(size=11),
                                            command=lambda: self._preview(True))
        self.preview_on_btn.pack(side="left", padx=(6, 2))

        self.preview_off_btn = ctk.CTkButton(self.sound_row, text="▶ Off", width=42, height=28,
                                             fg_color=C_WIDGET_BG, hover_color=C_LIGHT_HOVER,
                                             text_color=C_MAIN_FG, font=ctk.CTkFont(size=11),
                                             command=lambda: self._preview(False))
        self.preview_off_btn.pack(side="left", padx=(2, 0))
        
        # Sound volume row
        self.vol_label_frame = ctk.CTkFrame(self.sound_frame, fg_color="transparent")
        self.vol_label_frame.pack(fill="x", pady=(0, 1))
        
        self.vol_title_label = ctk.CTkLabel(self.vol_label_frame, text="Sound volume:",
                                            font=ctk.CTkFont(size=12), text_color=C_LABEL)
        self.vol_title_label.pack(side="left")
        
        saved_vol = int(self.config.get("sound_volume", 70))
        self.vol_value_label = ctk.CTkLabel(self.vol_label_frame, text=f"{saved_vol}%",
                                            font=ctk.CTkFont(size=12, weight="bold"), text_color=C_ACCENT)
        self.vol_value_label.pack(side="right")
        
        self.vol_var = ctk.IntVar(value=saved_vol)
        self.vol_slider = ctk.CTkSlider(self.sound_frame, from_=0, to=100, number_of_steps=20,
                                        variable=self.vol_var, command=self._on_vol_changed,
                                        button_color=C_MAIN_FG, button_hover_color=C_MAIN_HOVER,
                                        height=16)
        self.vol_slider.pack(fill="x", pady=(2, 4))
        self.vol_slider.bind("<ButtonRelease-1>", self._on_vol_released)
        
        # Initial pack states
        if self.pause_hotkey_var.get():
            self.pause_hotkey_frame.pack(pady=(2, 5), fill="x", after=self.pause_hotkey_check)
        if self.sound_var.get():
            self.sound_frame.pack(pady=(2, 5), fill="x", after=self.sound_check)

        # 7. App Blacklist (Exceptions)
        self.blacklist_enabled_var = ctk.BooleanVar(value=self.config.get("blacklist_enabled", False))
        self.blacklist_check = ctk.CTkCheckBox(self.content_frame, text="Enable App Blacklist",
                                               variable=self.blacklist_enabled_var,
                                               command=self._toggle_blacklist_visibility,
                                               text_color=C_CHECKBOX_TEXT, fg_color=C_MAIN_FG, hover_color=C_MAIN_HOVER,
                                               border_color=C_CHECKBOX_BORDER, checkmark_color=C_CHECKMARK, checkbox_width=18, checkbox_height=18)
        self.blacklist_check.pack(pady=(8, 4), anchor="w")

        self.blacklist_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        self.blacklist_row = ctk.CTkFrame(self.blacklist_frame, fg_color="transparent")
        self.blacklist_row.pack(fill="x", pady=(0, 2))
        
        self.blacklist_var = ctk.StringVar(value="Loading apps...")
        self.blacklist_dropdown = ctk.CTkOptionMenu(self.blacklist_row, values=["Loading apps..."],
                                               variable=self.blacklist_var,
                                               fg_color=C_WIDGET_BG, text_color=C_MAIN_FG,
                                               button_color=C_WIDGET_BG, button_hover_color=C_LIGHT_HOVER,
                                               dropdown_fg_color=C_WIDGET_BG, dropdown_text_color=C_MAIN_FG,
                                               height=28)
        self.blacklist_dropdown.pack(side="left", fill="x", expand=True)
        
        self.blacklist_add_btn = ctk.CTkButton(self.blacklist_row, text="Add", width=50, height=28,
                                               fg_color=C_MAIN_FG, hover_color=C_MAIN_HOVER, text_color=C_WIDGET_BG,
                                               command=self._add_blacklist_item)
        self.blacklist_add_btn.pack(side="left", padx=(6, 0))

        self.blacklist_scroll = ctk.CTkScrollableFrame(self.blacklist_frame, height=50, fg_color=C_SCROLL_BG, border_width=1, border_color=C_BORDER)
        self.blacklist_scroll.pack(fill="x", pady=(0, 4))
        
        self.blacklist_items = list(self.config.get("blacklist", []))
        self._blacklist_widgets = []
        self._refresh_blacklist_ui()
        
        if self.blacklist_enabled_var.get():
            self.blacklist_frame.pack(pady=(2, 5), fill="x", after=self.blacklist_check)

        # 8. App Theme
        self.theme_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.theme_frame.pack(fill="x", pady=(8, 0))
        
        self.theme_label = ctk.CTkLabel(self.theme_frame, text="App Theme:", 
                                        font=ctk.CTkFont(size=12, weight="bold"), text_color=C_LABEL)
        self.theme_label.pack(side="left")
        
        self.theme_var = ctk.StringVar(value=self.config.get("theme", "System"))
        self.theme_dropdown = ctk.CTkOptionMenu(self.theme_frame, values=["System", "Light", "Dark"],
                                                variable=self.theme_var,
                                                command=self._on_theme_changed,
                                                fg_color=C_WIDGET_BG, text_color=C_MAIN_FG,
                                                button_color=C_WIDGET_BG, button_hover_color=C_LIGHT_HOVER,
                                                dropdown_fg_color=C_WIDGET_BG, dropdown_text_color=C_MAIN_FG,
                                                height=28, width=100)
        self.theme_dropdown.pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self.close_window)
        
        # Load running apps after the UI is fully rendered
        self.after(50, self._start_loading_apps)

    def _start_loading_apps(self):
        import threading
        threading.Thread(target=self._load_running_apps_async, daemon=True).start()

    def _load_running_apps_async(self):
        apps = get_running_apps()
        if not apps:
            apps = ["No apps found"]
        self.after(0, lambda: self._update_apps_dropdown(apps))

    def _update_apps_dropdown(self, apps):
        self.blacklist_dropdown.configure(values=apps)
        if self.blacklist_var.get() == "Loading apps...":
            self.blacklist_var.set(apps[0])

    def _resize_to_fit(self):
        self.update_idletasks()
        req_h = self.winfo_reqheight()
        width = 345
        try:
            x = self.winfo_x()
            y = self.winfo_y()
            if x < 0 or y < 0:
                x = (self.winfo_screenwidth() // 2) - (width // 2)
                y = (self.winfo_screenheight() // 2) - (req_h // 2)
            self.geometry(f"{width}x{req_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{width}x{req_h}")

    def _toggle_pause_hotkey_visibility(self):
        if self.pause_hotkey_var.get():
            self.pause_hotkey_frame.pack(pady=(2, 5), fill="x", after=self.pause_hotkey_check)
        else:
            self.pause_hotkey_frame.pack_forget()
        self._resize_to_fit()

    def _toggle_blacklist_visibility(self):
        if self.blacklist_enabled_var.get():
            self.blacklist_frame.pack(pady=(2, 5), fill="x", after=self.blacklist_check)
        else:
            self.blacklist_frame.pack_forget()
        self._resize_to_fit()

    def _on_theme_changed(self, choice):
        if choice == "System":
            try:
                import darkdetect
                sys_theme = darkdetect.theme()
                if sys_theme:
                    ctk.set_appearance_mode(sys_theme)
            except Exception:
                pass
        ctk.set_appearance_mode(choice)

    def _toggle_sound_visibility(self):
        if self.sound_var.get():
            self.sound_frame.pack(pady=(2, 5), fill="x", after=self.sound_check)
        else:
            self.sound_frame.pack_forget()
        self._resize_to_fit()

    def _on_preset_selected(self, choice):
        play_preset_sound(choice, is_on=True, volume=self.vol_var.get())

    def _preview(self, is_on: bool):
        play_preset_sound(self.sound_var_choice.get(), is_on=is_on, volume=self.vol_var.get())

    def _on_vol_changed(self, value):
        self.vol_value_label.configure(text=f"{int(value)}%")

    def _on_vol_released(self, event=None):
        play_preset_sound(self.sound_var_choice.get(), is_on=True, volume=self.vol_var.get())

    def _add_blacklist_item(self):
        val = self.blacklist_var.get().strip().lower()
        if val == "no apps found":
            return
        if val and not val.endswith(".exe"):
            val += ".exe"
        if val and val not in self.blacklist_items:
            self.blacklist_items.append(val)
            self._refresh_blacklist_ui()

    def _remove_blacklist_item(self, item):
        if item in self.blacklist_items:
            self.blacklist_items.remove(item)
            self._refresh_blacklist_ui()

    def _refresh_blacklist_ui(self):
        for w in self._blacklist_widgets:
            w.destroy()
        self._blacklist_widgets.clear()
        
        for item in self.blacklist_items:
            row = ctk.CTkFrame(self.blacklist_scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)
            
            lbl = ctk.CTkLabel(row, text=item, text_color=C_LABEL, font=ctk.CTkFont(size=11))
            lbl.pack(side="left")
            
            btn = ctk.CTkButton(row, text="✕", width=20, height=20, 
                                fg_color="transparent", hover_color=C_DANGER_HOVER, text_color=C_DANGER,
                                font=ctk.CTkFont(size=10, weight="bold"),
                                command=lambda i=item: self._remove_blacklist_item(i))
            btn.pack(side="right")
            
            self._blacklist_widgets.append(row)

    def _has_custom_key(self):
        current_values = self.key_dropdown.cget("values")
        custom_items = [v for v in current_values if v not in KEY_OPTIONS and v != CUSTOM_KEY_LABEL]
        return len(custom_items) > 0 or self._selected_key_name not in KEY_OPTIONS

    def _update_delete_button_visibility(self):
        if self._has_custom_key():
            self.delete_key_btn.pack(side="left", padx=(6, 0))
        else:
            self.delete_key_btn.pack_forget()

    def _update_pause_delete_button_visibility(self):
        if self._selected_pause_key_name and self._selected_pause_key_name != "None":
            self.delete_pause_key_btn.pack(side="left", padx=(6, 0))
        else:
            self.delete_pause_key_btn.pack_forget()

    def delete_custom_key(self):
        dropdown_values = list(KEY_OPTIONS) + [CUSTOM_KEY_LABEL]
        self.key_dropdown.configure(values=dropdown_values)
        
        if self._selected_key_name not in KEY_OPTIONS:
            self._selected_vk = 0x14
            self._selected_key_name = "Caps Lock"
            self.key_var.set("Caps Lock")
            self.config["trigger_key"] = "Caps Lock"
            self.config["trigger_vk"] = 0x14
        
        self._update_delete_button_visibility()
        self.key_status_label.configure(text="Custom bind removed", text_color=C_MUTED)
        self.after(2000, lambda: self.key_status_label.configure(text=""))

    def delete_pause_key(self):
        self._selected_pause_vk = None
        self._selected_pause_key_name = "None"
        self.pause_key_btn.configure(text="Click to set key")
        self._update_pause_delete_button_visibility()
        self.pause_key_status_label.configure(text="Pause hotkey cleared", text_color=C_MUTED)
        self.after(2000, lambda: self.pause_key_status_label.configure(text=""))

    def _start_pause_key_binding(self):
        self._listening_for_pause_key = True
        self._listening_for_key = False
        self.pause_key_btn.configure(text="Press any key...")
        self.pause_key_status_label.configure(text="Press Esc to cancel", text_color=C_HELPER)
        self.bind("<KeyPress>", self._on_key_captured)
        self.focus_set()

    def _on_key_selected(self, choice):
        if choice == CUSTOM_KEY_LABEL:
            self._listening_for_key = True
            self._listening_for_pause_key = False
            self.key_var.set("Press any key...")
            self.key_status_label.configure(text="Press Esc to cancel", text_color=C_HELPER)
            self.bind("<KeyPress>", self._on_key_captured)
            self.focus_set()
        else:
            vk = name_to_vk(choice)
            if vk is not None:
                self._selected_key_name = choice
                self._selected_vk = vk
            self.key_status_label.configure(text="")
            self._update_delete_button_visibility()

    def _on_key_captured(self, event):
        if not self._listening_for_key and not self._listening_for_pause_key:
            return
        
        keysym = getattr(event, "keysym", "")
        vk = event.keycode

        if vk == 0x1B or keysym == "Escape":
            if self._listening_for_key:
                self._listening_for_key = False
                self.key_var.set(self._selected_key_name)
                self.key_status_label.configure(text="")
            elif self._listening_for_pause_key:
                self._listening_for_pause_key = False
                btn_txt = self._selected_pause_key_name if (self._selected_pause_key_name and self._selected_pause_key_name != "None") else "Click to set key"
                self.pause_key_btn.configure(text=btn_txt)
                self.pause_key_status_label.configure(text="")
            self.unbind("<KeyPress>")
            return

        if keysym in KEYSYM_TO_VK:
            vk = KEYSYM_TO_VK[keysym]
        elif vk == 0x10:
            if user32.GetAsyncKeyState(0xA1) & 0x8000:
                vk = 0xA1
            elif user32.GetAsyncKeyState(0xA0) & 0x8000:
                vk = 0xA0
        elif vk == 0x11:
            if user32.GetAsyncKeyState(0xA5) & 0x8000:
                vk = 0xA5
            elif user32.GetAsyncKeyState(0xA3) & 0x8000:
                vk = 0xA3
            elif user32.GetAsyncKeyState(0xA2) & 0x8000:
                vk = 0xA2
        elif vk == 0x12:
            if user32.GetAsyncKeyState(0xA5) & 0x8000:
                vk = 0xA5
            elif user32.GetAsyncKeyState(0xA4) & 0x8000:
                vk = 0xA4

        is_disallowed = (
            vk in DISALLOWED_VKS or
            keysym in ("Return", "KP_Enter", "Win_L", "Win_R", "Super_L", "Super_R") or
            "fn" in keysym.lower()
        )
        if is_disallowed:
            target_status = self.key_status_label if self._listening_for_key else self.pause_key_status_label
            curr_name = self._selected_key_name if self._listening_for_key else self._selected_pause_key_name

            if self._listening_for_key:
                self.key_var.set(curr_name)
            else:
                btn_txt = curr_name if (curr_name and curr_name != "None") else "Click to set key"
                self.pause_key_btn.configure(text=btn_txt)

            self._listening_for_key = False
            self._listening_for_pause_key = False
            self.unbind("<KeyPress>")

            disallow_name = DISALLOWED_VKS.get(vk)
            if not disallow_name:
                if "Enter" in keysym or "Return" in keysym:
                    disallow_name = "Enter"
                elif "Win" in keysym or "Super" in keysym:
                    disallow_name = "Windows key"
                elif "fn" in keysym.lower():
                    disallow_name = "Fn key"
                else:
                    disallow_name = "This key"
            target_status.configure(
                text=f"{disallow_name} cannot be used",
                text_color=C_ERROR
            )
            self.after(2500, lambda: target_status.configure(text=""))
            return

        name = vk_to_name(vk)

        if self._listening_for_key:
            self._listening_for_key = False
            self.unbind("<KeyPress>")
            self._selected_vk = vk
            self._selected_key_name = name

            current_values = list(KEY_OPTIONS)
            if name not in current_values:
                current_values.append(name)
            current_values.append(CUSTOM_KEY_LABEL)
            self.key_dropdown.configure(values=current_values)
            self.key_var.set(name)
            self.key_status_label.configure(text="")
            self._update_delete_button_visibility()
        elif self._listening_for_pause_key:
            self._listening_for_pause_key = False
            self.unbind("<KeyPress>")
            self._selected_pause_vk = vk
            self._selected_pause_key_name = name
            self.pause_key_btn.configure(text=name)
            self.pause_key_status_label.configure(text="")
            self._update_pause_delete_button_visibility()

    def update_ptt_label(self, value):
        self.ptt_value_label.configure(text=f"{int(value)} ms")

    def save_settings(self):
        self.config["trigger_key"] = self._selected_key_name
        self.config["trigger_vk"] = self._selected_vk
        self.config["switch_shortcut"] = self.combo_var.get()
        self.config["hold_threshold_ms"] = int(self.ptt_var.get())
        self.config["enable_shift_caps"] = self.shift_caps_var.get()
        self.config["start_with_windows"] = self.auto_start_var.get()
        
        self.config["pause_hotkey_enabled"] = self.pause_hotkey_var.get()
        self.config["pause_hotkey_key"] = self._selected_pause_key_name
        self.config["pause_hotkey_vk"] = self._selected_pause_vk

        self.config["sound_enabled"] = self.sound_var.get()
        self.config["sound_preset"] = self.sound_var_choice.get()
        self.config["sound_volume"] = int(self.vol_var.get())

        self.config["blacklist_enabled"] = self.blacklist_enabled_var.get()
        self.config["blacklist"] = self.blacklist_items
        self.config["theme"] = self.theme_var.get()

        set_startup_enabled(self.config["start_with_windows"])
        save_config(self.config)
        
        if self.on_save_callback:
            self.on_save_callback(self.config)
            
        self.close_window()

    def close_window(self):
        self.destroy()
        self.quit()

def _run_gui_thread(config, on_save_callback):
    global _window_open
    app = SettingsWindow(config, on_save_callback)
    
    app.update_idletasks()
    width = 345
    height = app.winfo_reqheight()
    x = (app.winfo_screenwidth() // 2) - (width // 2)
    y = (app.winfo_screenheight() // 2) - (height // 2)
    app.geometry(f"{width}x{height}+{x}+{y}")
    
    app.focus_force()
    app.mainloop()
    with _window_lock:
        _window_open = False

def open_settings_window_async(config=None, on_save_callback=None):
    global _window_open
    with _window_lock:
        if _window_open:
            return
        _window_open = True
    
    if config is None:
        config = load_config()
    
    t = threading.Thread(target=_run_gui_thread, args=(config, on_save_callback), daemon=True)
    t.start()

if __name__ == "__main__":
    open_settings_window_async()
    import time
    while _window_open:
        time.sleep(0.5)
