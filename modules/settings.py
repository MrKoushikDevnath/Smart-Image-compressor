import json
import os
import logging

class SettingsManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.settings = {
            "theme": "Dark",
            "format": "JPEG",
            "window_width": 1150,
            "window_height": 800
        }
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Update defaults with loaded data safely
                    for key, value in data.items():
                        if key in self.settings:
                            self.settings[key] = value
            except Exception as e:
                logging.error(f"Failed to load settings from {self.config_file}: {e}")

    def save_settings(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save settings to {self.config_file}: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value

