import json
from pathlib import Path


# Location of our JSON configuration file
CONFIG_FILE = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "lab_config.json"
)


def load_config():
    """Read the lab configuration from the JSON file."""

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_config(config):
    """Save the lab configuration to the JSON file."""

    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)


def get_config():
    """Return the current lab configuration."""

    return load_config()