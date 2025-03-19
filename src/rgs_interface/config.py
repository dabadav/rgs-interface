import sys
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from getpass import getpass

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

def load_config():
    config = load_config()
    
    if config:
        return config

    if is_interactive():
        print("No database credentials found. Please enter them.")
        db_user = prompt_non_empty("Enter DB User: ")
        if db_user is None:
            raise RuntimeError("Interactive input required but not available.")
        while True:
            db_pass = prompt_non_empty("Enter DB Password: ", is_password=True)
            if db_pass is None:
                raise RuntimeError("Interactive input required but not available.")
            db_pass_confirm = prompt_non_empty("Confirm DB Password: ", is_password=True)
            if db_pass == db_pass_confirm:
                break
            print("Passwords do not match. Please try again.")
        db_host = prompt_non_empty("Enter DB Host (e.g., localhost): ")
        if db_host is None:
            raise RuntimeError("Interactive input required but not available.")
        db_name = prompt_non_empty("Enter DB Name: ")
        if db_name is None:
            raise RuntimeError("Interactive input required but not available.")

        # Save credentials to .env and YAML
        save_to_env(db_user, db_pass, db_host, db_name)
        save_to_yaml(db_user, db_pass, db_host, db_name)

        return {"DB_USER": db_user, "DB_PASS": db_pass, "DB_HOST": db_host, "DB_NAME": db_name}
    else:
        raise RuntimeError("Database credentials are not set in environment variables or config file, and interactive input is not possible.")

credentials = load_config()
DB_USER = credentials["DB_USER"]
DB_PASS = credentials["DB_PASS"]
DB_HOST = credentials["DB_HOST"]
DB_NAME = credentials["DB_NAME"]
