import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure runtime directories exist
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'certificates.db'}")

# Application configuration
PROJECT_NAME = "Bulk Certificate Generator API"
PROJECT_DESCRIPTION = (
    "Production-ready backend service for asynchronously generating certificates in bulk."
)
VERSION = "1.0.0"
API_PREFIX = "/api"
