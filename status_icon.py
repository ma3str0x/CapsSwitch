import sys
import os
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from settings_gui import open_settings_window_async
from config import save_config, set_startup_enabled

def create_status_icon_image(is_enabled=True):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, "img", "logo_base.png")
    
    try:
        img = Image.open(img_path).convert("RGBA")
        border_color = (16, 185, 129, 255) if is_enabled else (239, 68, 68, 255)
        
        w, h = img.size
        new_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(new_img)
        
        bw = max(2, int(w * 0.08))
        draw.rounded_rectangle([(0, 0), (w-1, h-1)], radius=int(w*0.2), outline=border_color, width=bw)
        
        logo_size = (w - bw * 2, h - bw * 2)
        resized_logo = img.resize(logo_size, Image.Resampling.LANCZOS)
        
        offset_x = (w - logo_size[0]) // 2
        offset_y = (h - logo_size[1]) // 2
        new_img.paste(resized_logo, (offset_x, offset_y), mask=resized_logo)
        
        return new_img
    except Exception as e:
        print(f"Status icon error: {e}")
        return Image.new("RGBA", (64, 64), (0, 0, 0, 0))

class StatusIconApp:
    def __init__(self, config, on_config_change, on_exit):
        self.config = config
        self.on_config_change = on_config_change
        self.on_exit = on_exit
        self.icon = None

    def update_icon_image(self):
        if self.icon:
            self.icon.icon = create_status_icon_image(self.config.get("enabled", True))

    def toggle_enabled(self, icon=None, item=None):
        new_state = not self.config.get("enabled", True)
        self.config["enabled"] = new_state
        save_config(self.config)
        self.update_icon_image()
        if self.on_config_change:
            self.on_config_change(self.config)

    def toggle_startup(self, icon=None, item=None):
        new_state = not self.config.get("start_with_windows", False)
        self.config["start_with_windows"] = new_state
        set_startup_enabled(new_state)
        save_config(self.config)
        if self.on_config_change:
            self.on_config_change(self.config)

    def open_settings(self, icon=None, item=None):
        def _on_save(updated_config):
            self.config.update(updated_config)
            self.update_icon_image()
            if self.on_config_change:
                self.on_config_change(self.config)

        open_settings_window_async(self.config, _on_save)

    def exit_app(self, icon=None, item=None):
        if self.icon:
            self.icon.stop()
        if self.on_exit:
            self.on_exit()

    def build_menu(self):
        return pystray.Menu(
            item(
                lambda text: "CapsSwitch: Active" if self.config.get("enabled", True) else "CapsSwitch: Paused",
                self.toggle_enabled,
                default=True
            ),
            item("Settings...", self.open_settings),
            pystray.Menu.SEPARATOR,
            item("Exit", self.exit_app)
        )

    def run(self):
        initial_img = create_status_icon_image(self.config.get("enabled", True))
        self.icon = pystray.Icon(
            "CapsSwitch",
            initial_img,
            "CapsSwitch — Language Switcher",
            menu=self.build_menu()
        )
        self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()
