import sys
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from getpass import getpass

# Credential sources, in order: environment, ./.env, ~/.rgs_config.yaml.
# DB_*        → SqlBackend.from_config()
# RGS_API_*   → HttpBackend.from_config()

CONFIG_FILE = Path.home() / ".rgs_config.yaml"  # Store in user home dir
ENV_FILE = Path(".env")  # Local env file

def is_interactive():
    return sys.stdin.isatty()

def prompt_non_empty(prompt_text, is_password=False):
    """Prompt user for input and ensure it's not empty."""
    while True:
        value = getpass(prompt_text) if is_password else input(prompt_text)
        if value.strip():
            return value
        print("Input cannot be empty. Please try again.")

def save_to_env(db_user, db_pass, db_host, db_name):
    """Save credentials to .env file."""
    with open(ENV_FILE, "w") as f:
        f.write(f"DB_USER={db_user}\n")
        f.write(f"DB_PASS={db_pass}\n")
        f.write(f"DB_HOST={db_host}\n")
        f.write(f"DB_NAME={db_name}\n")

def save_to_yaml(db_user, db_pass, db_host, db_name):
    """Save credentials to YAML config file."""
    with open(CONFIG_FILE, "w") as f:
        yaml.dump({"DB_USER": db_user, "DB_PASS": db_pass, "DB_HOST": db_host, "DB_NAME": db_name}, f)

def get_config():
    
    # Load environment variables from .env file, if it exists
    load_dotenv(ENV_FILE)

    # Attempt to retrieve configuration from environment variables
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")

    if all([db_user, db_pass, db_host, db_name]):
        return {"DB_USER": db_user, "DB_PASS": db_pass, "DB_HOST": db_host, "DB_NAME": db_name}

    # Attempt to retrieve configuration from YAML config file
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
            if all(key in config for key in ["DB_USER", "DB_PASS", "DB_HOST", "DB_NAME"]):
                return config

    # If neither source provides the configuration, return None
    return None

# ---------------------------------------------------------------------------
# API client configuration (rgs-cli / HttpBackend)
# ---------------------------------------------------------------------------

API_KEYS = ("RGS_API_URL", "RGS_API_TOKEN")


def get_api_config():
    """API url + token from env (.env honoured) or ~/.rgs_config.yaml; None if incomplete."""
    load_dotenv(ENV_FILE)
    cfg = {k: os.getenv(k) for k in API_KEYS}
    if all(cfg.values()):
        return cfg
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}
        cfg = {k: data.get(k) for k in API_KEYS}
        if all(cfg.values()):
            return cfg
    return None


def save_yaml(**values):
    """Merge key/values into ~/.rgs_config.yaml (keeps existing keys)."""
    data = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}
    data.update({k: v for k, v in values.items() if v is not None})
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(data, f)
    CONFIG_FILE.chmod(0o600)
