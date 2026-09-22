<p align="center">
  <img src="img/logo_base.png" alt="CapsSwitch Logo" width="120" />
</p>

<h1 align="center">CapsSwitch</h1>

<p align="center">
  A lightweight Windows utility that turns Caps Lock or any key into a fast language switcher while preserving Push-to-Talk functionality for games and voice chat.
</p>

---

## How it works

Switching input languages in Windows typically requires combinations like `Win+Space` or `Alt+Shift`. CapsSwitch lets you switch layouts with a single key (Caps Lock, Tilde, or any custom key) without losing Push-to-Talk functionality in Discord or games.

A quick tap triggers your configured language switch shortcut. Holding the key keeps it active for voice chat, and releasing it will not switch the language. When using Caps Lock, standard uppercase toggle remains available via `Shift + Caps Lock`.

## Settings

Right-click the app icon to configure:

- **Switch language key**: Caps Lock, Tilde, or custom key
- **Windows combination**: `Win+Space`, `Alt+Shift`, or `Ctrl+Shift`
- **Push-to-Talk delay**: Threshold in milliseconds
- **Shift + Caps Lock switches UPPERCASE**: Toggle behavior
- **Start automatically with Windows**: Toggle autostart

## How to run

### Standalone (recommended)

Download the latest **[CapsSwitch.exe](../../releases/latest)** from the Releases page and run it. No Python installation required.

### From source

1. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

2. Run silently (no console window):
   ```cmd
   CapsSwitch.vbs
   ```
   Or with console:
   ```cmd
   run_console.bat
   ```

## Requirements

- Windows 10 / 11
- Python 3.10+ (only when running from source)
