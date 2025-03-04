import os
from dotenv import load_dotenv

# Load .env only if credentials are missing in the system environment
if not all([os.getenv("DB_USER"), os.getenv("DB_PASSWORD"), os.getenv("DB_HOST"), os.getenv("DB_NAME")]):
    load_dotenv()
    print("[INFO] Loaded environment variables from .env")
