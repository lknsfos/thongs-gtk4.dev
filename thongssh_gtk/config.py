import json
import os
import logging
from pathlib import Path

# --- Global Constants ---
CONFIG_DIR = Path.home() / ".config" / "thongssh"
CONFIG_FILE = CONFIG_DIR / "hosts.json" 
from gi.repository import GLib

# Default template for a new config file
DEFAULT_CONFIG_DATA = {
    "type": "group",
    "name": "Root",
    "children": [
        {
            "type": "host",
            "config": {
                "name": "Example Host",
                "host": "user@example.com",
                "port": None,
                "key_path": None,
                "compat_old_systems": False,
                "ssh_options": None,
                "forward_x": False,
                "forward_agent": False
            }
        }
    ]
}

# Template for migration. Add ALL new fields here!
HOST_CONFIG_TEMPLATE = {
    "protocol": "ssh",
    "name": None,
    "host": None,
    "port": None,
    "key_path": None,
    "compat_old_systems": False,
    "ssh_options": None,
    "forward_x": False,
    "forward_agent": False,
    "telnet_binary": False,
    "telnet_local_echo": False,
}


def _recursive_migrate(node):
    needs_save = False
    if node.get("type") == "host":
        if "config" not in node:
            node["config"] = {}
            needs_save = True
        for key, default_value in HOST_CONFIG_TEMPLATE.items():
            if key not in node["config"]:
                node["config"][key] = default_value
                needs_save = True
    elif node.get("type") == "group":
        # ✨ Add 'expanded' field for groups if it doesn't exist
        if "expanded" not in node:
            node["expanded"] = True  # Groups are expanded by default
            needs_save = True

        if "children" in node:
            migrated_children = []
            for child in node["children"]:
                migrated_child, child_needs_save = _recursive_migrate(child)
                migrated_children.append(migrated_child)
                if child_needs_save:
                    needs_save = True
            node["children"] = migrated_children
    return node, needs_save


def load_and_migrate_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        logging.info("Config file not found, creating a new one...")
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG_DATA, f, indent=4)
        return DEFAULT_CONFIG_DATA

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        needs_save_after_wrap = False
        if isinstance(data, list):
            logging.info("Old config format (list) detected, wrapping in Root...")
            data = {"type": "group", "name": "Root", "children": data}
            needs_save_after_wrap = True

        migrated_data, needs_migration_save = _recursive_migrate(data)

        if needs_save_after_wrap or needs_migration_save:
            logging.info("Updating config file (migration)...")
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(migrated_data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.error(f"Failed to save migrated config: {e}")

        return migrated_data
    except json.JSONDecodeError:
        logging.error(f"ОШИБКА: Конфиг {CONFIG_FILE} поврежден. Создаю резервную копию.")
        os.rename(CONFIG_FILE, f"{CONFIG_FILE}.bak")
        return load_and_migrate_config()


def save_config(config_data):
    """Saves the given dictionary to hosts.json."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Failed to save config: {e}")