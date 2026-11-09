from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")
DEFAULT_MODEL_PATH = ROOT_DIR / "backend" / "app" / "artifacts" / "project_model" / "modelo_riesgo_api.pkl"
DEFAULT_METADATA_PATH = ROOT_DIR / "backend" / "app" / "artifacts" / "project_model" / "model_metadata.json"


def env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else ROOT_DIR / path


MODEL_PATH = env_path("MODEL_PATH", DEFAULT_MODEL_PATH)
MODEL_METADATA_PATH = env_path("MODEL_METADATA_PATH", DEFAULT_METADATA_PATH)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip()

