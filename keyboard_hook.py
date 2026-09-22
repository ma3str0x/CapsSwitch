import ctypes
from ctypes import wintypes
import threading

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_SCANCODE = 0x0008

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SPACE = 0x20
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_CAPITAL = 0x14
VK_SCROLL = 0x91
VK_NUMLOCK = 0x90
VK_RCONTROL = 0xA3
VK_RMENU = 0xA5

KEY_NAME_TO_VK = {
    "Caps Lock": VK_CAPITAL,
    "Scroll Lock": VK_SCROLL,
    "Pause / Break": 0x13,
    "Right Ctrl": VK_RCONTROL,
    "Right Alt": VK_RMENU,
    "Tilde (~)": 0xC0,
}

MAGIC_EXTRA_INFO = 0xCA9501

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK

user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_long

user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]

user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL

user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_void_p]

INPUT_KEYBOARD = 1

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _anonymous_ = ("_union",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_union", _INPUT_UNION),
    ]

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT

user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

class KeyboardHook:
    def __init__(self, config_getter):
        self.config_getter = config_getter
        self.hook_id = None
        self.hook_thread = None
        self.hook_thread_id = None
        self._hook_proc_ref = None
        self.running = False
        
        self.is_pressed = False
        self.hold_triggered = False
        self.hold_timer = None
        self.initial_caps_state = 0
        self.lock = threading.Lock()
        self._ready_event = threading.Event()

    def get_trigger_vk(self):
        cfg = self.config_getter()
        vk = cfg.get("trigger_vk")
        if vk is not None:
            return int(vk)
        key_name = cfg.get("trigger_key", "Caps Lock")
        return KEY_NAME_TO_VK.get(key_name, VK_CAPITAL)

    def is_shift_down(self):
        return bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)

    def send_key_event(self, vk, is_up=False, is_extended=False):
        scan_code = user32.MapVirtualKeyW(vk, 0)
        flags = 0
        if is_up:
            flags |= KEYEVENTF_KEYUP
        if is_extended or vk in (VK_RCONTROL, VK_RMENU, VK_LWIN, VK_RWIN):
            flags |= KEYEVENTF_EXTENDEDKEY

        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = wintypes.WORD(vk)
        inp.ki.wScan = wintypes.WORD(scan_code)
        inp.ki.dwFlags = wintypes.DWORD(flags)
        inp.ki.time = 0
        inp.ki.dwExtraInfo = ctypes.c_void_p(MAGIC_EXTRA_INFO)

        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def toggle_real_capslock(self):
        self.send_key_event(VK_CAPITAL, is_up=False)
        self.send_key_event(VK_CAPITAL, is_up=True)

    def switch_layout(self):
        cfg = self.config_getter()
        method = cfg.get("switch_shortcut", "Win+Space")
        
        if method == "Alt+Shift":
            self.send_key_event(VK_MENU, is_up=False)
            self.send_key_event(VK_SHIFT, is_up=False)
            self.send_key_event(VK_SHIFT, is_up=True)
            self.send_key_event(VK_MENU, is_up=True)
        elif method == "Ctrl+Shift":
            self.send_key_event(VK_CONTROL, is_up=False)
            self.send_key_event(VK_SHIFT, is_up=False)
            self.send_key_event(VK_SHIFT, is_up=True)
            self.send_key_event(VK_CONTROL, is_up=True)
        else:
            self.send_key_event(VK_LWIN, is_up=False)
            self.send_key_event(VK_SPACE, is_up=False)
            self.send_key_event(VK_SPACE, is_up=True)
            self.send_key_event(VK_LWIN, is_up=True)

    def _on_hold_threshold_reached(self, trigger_vk):
        with self.lock:
            if self.is_pressed and not self.hold_triggered:
                self.hold_triggered = True
                self.send_key_event(trigger_vk, is_up=False)

    def hook_procedure(self, nCode, wParam, lParam):
        if nCode < 0:
            return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

        kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        
        # Ignore self-injected events
        if kbd.dwExtraInfo == MAGIC_EXTRA_INFO:
            return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

        cfg = self.config_getter()
        if not cfg.get("enabled", True):
            return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

        trigger_vk = self.get_trigger_vk()

        is_trigger = (kbd.vkCode == trigger_vk)
        if not is_trigger:
            if trigger_vk == VK_SHIFT and kbd.vkCode in (0xA0, 0xA1):
                is_trigger = True
            elif trigger_vk == VK_CONTROL and kbd.vkCode in (0xA2, 0xA3):
                is_trigger = True
            elif trigger_vk == VK_MENU and kbd.vkCode in (0xA4, 0xA5):
                is_trigger = True

        if is_trigger:
            is_down_event = (wParam in (WM_KEYDOWN, WM_SYSKEYDOWN))
            is_up_event = (wParam in (WM_KEYUP, WM_SYSKEYUP))

            if is_down_event:
                with self.lock:
                    if trigger_vk == VK_CAPITAL and cfg.get("enable_shift_caps", True) and self.is_shift_down():
                        self.toggle_real_capslock()
                        self.is_pressed = False
                        self.hold_triggered = False
                        return 1

                    if not self.is_pressed:
                        self.is_pressed = True
                        self.hold_triggered = False
                        self.initial_caps_state = (user32.GetKeyState(VK_CAPITAL) & 1)
                        
                        threshold_sec = max(50, cfg.get("hold_threshold_ms", 220)) / 1000.0
                        if self.hold_timer:
                            self.hold_timer.cancel()
                        self.hold_timer = threading.Timer(
                            threshold_sec,
                            self._on_hold_threshold_reached,
                            args=[trigger_vk]
                        )
                        self.hold_timer.daemon = True
                        self.hold_timer.start()

                return 1

            elif is_up_event:
                with self.lock:
                    if self.hold_timer:
                        self.hold_timer.cancel()
                        self.hold_timer = None

                    was_holding = self.hold_triggered
                    was_pressed = self.is_pressed
                    
                    self.is_pressed = False
                    self.hold_triggered = False

                    if was_holding:
                        self.send_key_event(trigger_vk, is_up=True)
                        # Restore Caps Lock state if changed by hold
                        if trigger_vk == VK_CAPITAL:
                            curr_state = (user32.GetKeyState(VK_CAPITAL) & 1)
                            if curr_state != self.initial_caps_state:
                                self.toggle_real_capslock()
                    elif was_pressed:
                        self.switch_layout()

                return 1

        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def _hook_thread_main(self):
        self.hook_thread_id = kernel32.GetCurrentThreadId()
        self._hook_proc_ref = HOOKPROC(self.hook_procedure)

        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            kernel32.GetModuleHandleW(None),
            0
        )

        if not self.hook_id:
            self.running = False
            self._ready_event.set()
            return

        self.running = True
        self._ready_event.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
        self.running = False

    def start(self):
        if self.running or self.hook_thread:
            return
        self._ready_event.clear()
        self.hook_thread = threading.Thread(target=self._hook_thread_main, daemon=True)
        self.hook_thread.start()
        self._ready_event.wait(timeout=2.0)

    def stop(self):
        if not self.running:
            return
        if self.hook_thread_id:
            user32.PostThreadMessageW(self.hook_thread_id, WM_QUIT, 0, 0)
        if self.hook_thread and self.hook_thread.is_alive():
            self.hook_thread.join(timeout=2.0)
        self.hook_thread = None
        self.hook_thread_id = None
        self.running = False
