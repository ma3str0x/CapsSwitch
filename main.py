import os
import sys
import ctypes
from ctypes import wintypes
import atexit

from config import load_config, get_live_config
from keyboard_hook import KeyboardHook
from status_icon import StatusIconApp

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ma3str0x.capsswitch.app')
except Exception:
    pass

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

kernel32 = ctypes.windll.kernel32
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

MUTEX_NAME = "Local\\CapsSwitch_User_App_Mutex"
ERROR_ALREADY_EXISTS = 183

def acquire_single_instance_mutex():
    try:
        mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not mutex:
            return True
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(mutex)
            return None
        return mutex
    except Exception:
        return True

def main():
    mutex = acquire_single_instance_mutex()
    if not mutex:
        sys.exit(0)

    config = load_config()

    hook = KeyboardHook(get_live_config)
    hook.start()

    def on_config_change(updated_config):
        nonlocal config
        config = updated_config

    def on_exit():
        hook.stop()
        if mutex:
            kernel32.CloseHandle(mutex)

    atexit.register(on_exit)

    app = StatusIconApp(config, on_config_change, on_exit)
    hook.on_toggle_pause = app.toggle_enabled
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        on_exit()
        import os
        os._exit(0)

if __name__ == "__main__":
    main()
