import json
import os

CONFIG_PATH = os.path.join(os.getcwd(), 'config.json')

def load_config():
    """Loads the configuration from config.json."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config_data):
    """Saves the configuration to config.json."""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config_data, f, indent=4)
