"""
Glean Configuration Module

Load and manage configuration from config.yaml.
"""

import os
from pathlib import Path
from typing import Any
import yaml


DEFAULT_CONFIG = {
    "database": {
        "path": "db/glean.db"
    },
    "logging": {
        "level": "INFO"
    }
}


def find_config_file() -> Path | None:
    """Find the config file, checking common locations."""
    locations = [
        Path("config.yaml"),
        Path("config.yml"),
        Path.home() / ".config" / "glean" / "config.yaml",
    ]

    for path in locations:
        if path.exists():
            return path

    return None


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Optional explicit path to config file.

    Returns:
        Configuration dictionary with defaults applied.
    """
    config = DEFAULT_CONFIG.copy()

    if config_path:
        path = Path(config_path)
    else:
        path = find_config_file()

    if path and path.exists():
        with open(path) as f:
            file_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, file_config)

    # Override with environment variables
    if os.environ.get("GLEAN_DB_PATH"):
        config["database"]["path"] = os.environ["GLEAN_DB_PATH"]

    if os.environ.get("ANTHROPIC_API_KEY"):
        config.setdefault("api_keys", {})["anthropic"] = os.environ["ANTHROPIC_API_KEY"]

    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_api_key(config: dict, key_name: str) -> str | None:
    """Get an API key from config, with environment variable fallback."""
    # Check environment first
    env_var = f"{key_name.upper()}_API_KEY"
    if os.environ.get(env_var):
        return os.environ[env_var]

    # Check config
    return config.get("api_keys", {}).get(key_name)
