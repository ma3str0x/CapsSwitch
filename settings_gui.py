import os
import sys

def _fix_tcl_tk():
    if getattr(sys, 'frozen', False):
        return
    if "TCL_LIBRARY" in os.environ and "TK_LIBRARY" in os.environ:
        return
    candidates = [
        getattr(sys, "base_prefix", sys.prefix),
        os.path.dirname(os.path.realpath(sys.executable)),
    ]
    venv_cfg = os.path.join(sys.prefix, "pyvenv.cfg")
    if os.path.isfile(venv_cfg):
        with open(venv_cfg, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip().lower().startswith("home"):
                    home_dir = line.split("=", 1)[1].strip()
                    candidates.extend([home_dir, os.path.dirname(home_dir)])
                    break
    appdata = os.environ.get("LOCALAPPDATA", "")
    if appdata:
        base_programs = os.path.join(appdata, "Programs", "Python")
        if os.path.isdir(base_programs):
            for d in os.listdir(base_programs):
                candidates.append(os.path.join(base_programs, d))
    for prefix in candidates:
        for sub, var in [("tcl/tcl8.6", "TCL_LIBRARY"), ("tcl/tk8.6", "TK_LIBRARY")]:
            p = os.path.join(prefix, sub.replace("/", os.sep))
            if os.path.isdir(p) and var not in os.environ:
                os.environ[var] = p
        if "TCL_LIBRARY" in os.environ and "TK_LIBRARY" in os.environ:
            return

_fix_tcl_tk()

import threading
import customtkinter as ctk
from config import load_config, save_config, set_startup_enabled

_window_open = False
_window_lock = threading.Lock()

KEY_OPTIONS = ['Caps Lock', 'Tilde (~)']
CUSTOM_KEY_LABEL = 'Custom key...'

KEY_NAME_TO_VK = {
    'Caps Lock': 0x14,
    'Tilde (~)': 0xC0,
}

VK_NAMES = {
    0x14: "Caps Lock", 0xC0: "Tilde (~)",
    0x10: "Shift", 0xA0: "Left Shift", 0xA1: "Right Shift",
    0x11: "Ctrl", 0xA2: "Left Ctrl", 0xA3: "Right Ctrl",
    0x12: "Alt", 0xA4: "Left Alt", 0xA5: "Right Alt",
    0x91: "Scroll Lock", 0x13: "Pause / Break",
    0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4", 0x74: "F5",
    0x75: "F6", 0x76: "F7", 0x77: "F8", 0x78: "F9", 0x79: "F10",
    0x7A: "F11", 0x7B: "F12", 0x2C: "Print Screen", 0x2D: "Insert",
    0x2E: "Delete", 0x24: "Home", 0x23: "End", 0x21: "Page Up", 0x22: "Page Down",
    0x90: "Num Lock", 0x6F: "Num /", 0x6A: "Num *", 0x6D: "Num -", 0x6B: "Num +",
    0x60: "Num 0", 0x61: "Num 1", 0x62: "Num 2", 0x63: "Num 3", 0x64: "Num 4",
    0x65: "Num 5", 0x66: "Num 6", 0x67: "Num 7", 0x68: "Num 8", 0x69: "Num 9",
    0x6E: "Num .",
    0xBF: "/", 0xBE: ".", 0xBC: ",", 0xBA: ";", 0xDE: "'", 0xDB: "[", 0xDD: "]",
    0xDC: "\\", 0xBD: "-", 0xBB: "=",
    0x08: "Backspace", 0x09: "Tab", 0x20: "Space",
    0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
    0x0D: "Enter", 0x5B: "Windows", 0x5C: "Windows", 0x1B: "Escape",
}

KEYSYM_TO_VK = {
    "Shift_L": 0xA0,
    "Shift_R": 0xA1,
    "Control_L": 0xA2,
    "Control_R": 0xA3,
    "Alt_L": 0xA4,
    "Alt_R": 0xA5,
    "ISO_Level3_Shift": 0xA5,
    "Return": 0x0D,
    "KP_Enter": 0x0D,
    "Win_L": 0x5B,
    "Win_R": 0x5C,
    "Super_L": 0x5B,
    "Super_R": 0x5C,
}

DISALLOWED_VKS = {
    0x0D: "Enter",
    0x5B: "Windows key",
    0x5C: "Windows key",
    0xFF: "Fn key",
    0x00: "Special key",
}

def vk_to_name(vk_code):
    if vk_code in VK_NAMES:
        return VK_NAMES[vk_code]
    if 0x41 <= vk_code <= 0x5A:
        return chr(vk_code)
    if 0x30 <= vk_code <= 0x39:
        return chr(vk_code)
    return f"Key 0x{vk_code:02X}"

def name_to_vk(name):
    if name in KEY_NAME_TO_VK:
        return KEY_NAME_TO_VK[name]
    for vk, n in VK_NAMES.items():
        if n == name:
            return vk
    if len(name) == 1:
        return ord(name.upper())
    if name.startswith("Key 0x"):
        try:
            return int(name.replace("Key 0x", ""), 16)
        except ValueError:
            pass
    return None

COMBO_OPTIONS = ['Alt+Shift', 'Ctrl+Shift', 'Win+Space']

class SettingsWindow(ctk.CTk):
    def __init__(self, config, on_save_callback=None):
        super().__init__()
        self.config = config
        self.on_save_callback = on_save_callback
        
        self.title("CapsSwitch")
        self.geometry("340x405")
        self.resizable(False, False)
        
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('capsswitch.settings.ui.1')
        except Exception:
            pass

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_png_path = os.path.join(base_dir, "img", "logo_base.png")
        icon_ico_path = os.path.join(base_dir, "img", "logo_base.ico")
        
        if os.path.exists(icon_png_path):
            from PIL import Image
            if not os.path.exists(icon_ico_path):
                try:
                    img = Image.open(icon_png_path)
                    img.save(icon_ico_path, format="ICO", sizes=[(64, 64)])
                except Exception:
                    pass
            
            if os.path.exists(icon_ico_path):
                self.iconbitmap(icon_ico_path)
                
            try:
                from PIL import ImageTk
                self.iconphoto(False, ImageTk.PhotoImage(Image.open(icon_png_path)))
            except Exception:
                pass
        
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#fffefb")
        
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(padx=20, pady=(14, 14), fill="both", expand=True)
        
        self.title_label = ctk.CTkLabel(self.main_frame, text="Settings", 
                                        font=ctk.CTkFont(size=17, weight="bold"), text_color="#24211e")
        self.title_label.pack(pady=(0, 10), anchor="w")
        
        self.key_label = ctk.CTkLabel(self.main_frame, text="Switch language key:", 
                                      font=ctk.CTkFont(size=12), text_color="#3b3632")
        self.key_label.pack(anchor="w")
        
        self.key_row_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.key_row_frame.pack(pady=(2, 2), fill="x")
        
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
                                              fg_color="#ffffff", text_color="#2b2724", 
                                              button_color="#ffffff", button_hover_color="#f0ebe0",
                                              dropdown_fg_color="#ffffff", dropdown_text_color="#2b2724",
                                              height=28)
        self.key_dropdown.pack(side="left", fill="x", expand=True)
        
        self.delete_key_btn = ctk.CTkButton(self.key_row_frame, text="✕", width=28, height=28,
                                            fg_color="#ffffff", hover_color="#feebe8",
                                            text_color="#c94a4a", font=ctk.CTkFont(size=12, weight="bold"),
                                            command=self.delete_custom_key)
        
        self.key_status_label = ctk.CTkLabel(self.main_frame, text="", 
                                             font=ctk.CTkFont(size=11), text_color="#888078")
        self.key_status_label.pack(anchor="w", pady=(0, 4))
        
        self._update_delete_button_visibility()
        
        self.combo_label = ctk.CTkLabel(self.main_frame, text="Windows system combination:", 
                                        font=ctk.CTkFont(size=12), text_color="#3b3632")
        self.combo_label.pack(anchor="w")
        
        self.combo_var = ctk.StringVar(value=self.config.get("switch_shortcut", "Win+Space"))
        self.combo_dropdown = ctk.CTkOptionMenu(self.main_frame, values=COMBO_OPTIONS, variable=self.combo_var,
                                                fg_color="#ffffff", text_color="#2b2724", 
                                                button_color="#ffffff", button_hover_color="#f0ebe0",
                                                dropdown_fg_color="#ffffff", dropdown_text_color="#2b2724",
                                                height=28)
        self.combo_dropdown.pack(pady=(2, 8), fill="x")
        
        self.ptt_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.ptt_frame.pack(fill="x", pady=(0, 2))
        
        self.ptt_label = ctk.CTkLabel(self.ptt_frame, text="Push-to-Talk delay:", 
                                      font=ctk.CTkFont(size=12), text_color="#3b3632")
        self.ptt_label.pack(side="left")
        
        self.ptt_value_label = ctk.CTkLabel(self.ptt_frame, text=f"{self.config.get('hold_threshold_ms', 220)} ms", 
                                            font=ctk.CTkFont(size=12, weight="bold"), text_color="#825633")
        self.ptt_value_label.pack(side="right")
        
        self.ptt_var = ctk.IntVar(value=self.config.get("hold_threshold_ms", 220))
        self.ptt_slider = ctk.CTkSlider(self.main_frame, from_=100, to=500, number_of_steps=40,
                                        variable=self.ptt_var, command=self.update_ptt_label,
                                        button_color="#2b2724", button_hover_color="#1a1715",
                                        height=16)
        self.ptt_slider.pack(fill="x", pady=(2, 10))
        
        self.shift_caps_var = ctk.BooleanVar(value=self.config.get("enable_shift_caps", True))
        self.shift_caps_check = ctk.CTkCheckBox(self.main_frame, text="Shift + Caps Lock switches UPPERCASE",
                                                variable=self.shift_caps_var,
                                                text_color="#36322e", fg_color="#2b2724", hover_color="#1a1715",
                                                border_color="#d8d2c7", checkbox_width=18, checkbox_height=18)
        self.shift_caps_check.pack(pady=(0, 6), anchor="w")
        
        self.auto_start_var = ctk.BooleanVar(value=self.config.get("start_with_windows", False))
        self.auto_start_check = ctk.CTkCheckBox(self.main_frame, text="Start automatically with Windows",
                                                variable=self.auto_start_var,
                                                text_color="#36322e", fg_color="#2b2724", hover_color="#1a1715",
                                                border_color="#d8d2c7", checkbox_width=18, checkbox_height=18)
        self.auto_start_check.pack(pady=(0, 10), anchor="w")
        
        self.sep = ctk.CTkFrame(self.main_frame, height=1, fg_color="#ece6dc")
        self.sep.pack(fill="x", pady=(0, 8))
        
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x")
        
        self.save_btn = ctk.CTkButton(self.btn_frame, text="Save", command=self.save_settings,
                                      fg_color="#2b2724", hover_color="#1a1715", text_color="#ffffff", width=75, height=28)
        self.save_btn.pack(side="right", padx=(8, 0))
        
        self.cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", command=self.close_window,
                                        fg_color="transparent", hover_color="#f0ebe0", text_color="#5c554e", width=75, height=28)
        self.cancel_btn.pack(side="right")
        
        self.protocol("WM_DELETE_WINDOW", self.close_window)
    
    def _has_custom_key(self):
        current_values = self.key_dropdown.cget("values")
        custom_items = [v for v in current_values if v not in KEY_OPTIONS and v != CUSTOM_KEY_LABEL]
        return len(custom_items) > 0 or self._selected_key_name not in KEY_OPTIONS

    def _update_delete_button_visibility(self):
        if self._has_custom_key():
            self.delete_key_btn.pack(side="left", padx=(6, 0))
        else:
            self.delete_key_btn.pack_forget()

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
        self.key_status_label.configure(text="Custom bind removed", text_color="#5c554e")
        self.after(2000, lambda: self.key_status_label.configure(text=""))

    def _on_key_selected(self, choice):
        if choice == CUSTOM_KEY_LABEL:
            self._listening_for_key = True
            self.key_var.set("Press any key...")
            self.key_status_label.configure(text="Press Esc to cancel", text_color="#888078")
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
        if not self._listening_for_key:
            return
        
        keysym = getattr(event, "keysym", "")
        vk = event.keycode

        if vk == 0x1B or keysym == "Escape":
            self._listening_for_key = False
            self.unbind("<KeyPress>")
            self.key_var.set(self._selected_key_name)
            self.key_status_label.configure(text="")
            return

        if keysym in KEYSYM_TO_VK:
            vk = KEYSYM_TO_VK[keysym]
        elif vk == 0x10:
            if user32.GetAsyncKeyState(0xA1) & 0x8000:
                vk = 0xA1
            elif user32.GetAsyncKeyState(0xA0) & 0x8000:
                vk = 0xA0
        elif vk == 0x11:
            # AltGr / Right Alt sends fake Ctrl first in Windows
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
            self._listening_for_key = False
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
            self.key_var.set(self._selected_key_name)
            self.key_status_label.configure(
                text=f"{disallow_name} cannot be used as trigger",
                text_color="#b83232"
            )
            self.after(2500, lambda: self.key_status_label.configure(text=""))
            return

        self._listening_for_key = False
        self.unbind("<KeyPress>")

        name = vk_to_name(vk)
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
        
    def update_ptt_label(self, value):
        self.ptt_value_label.configure(text=f"{int(value)} ms")
        
    def save_settings(self):
        self.config["trigger_key"] = self._selected_key_name
        self.config["trigger_vk"] = self._selected_vk
        self.config["switch_shortcut"] = self.combo_var.get()
        self.config["hold_threshold_ms"] = int(self.ptt_var.get())
        self.config["enable_shift_caps"] = self.shift_caps_var.get()
        self.config["start_with_windows"] = self.auto_start_var.get()
        
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
    width = 340
    height = 390
    x = (app.winfo_screenwidth() // 2) - (width // 2)
    y = (app.winfo_screenheight() // 2) - (height // 2)
    app.geometry(f'{width}x{height}+{x}+{y}')
    
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
