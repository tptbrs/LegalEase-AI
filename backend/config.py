"""Centralised settings for LegalEase AI.

Every pipeline module reads configuration through `get_settings()` rather than
touching `os.environ` directly. This keeps the system testable (override via
env vars or a custom `.env`) and gives one obvious place to change defaults.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR: Path = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Filesystem paths ---
    data_dir: Path = BACKEND_DIR / "data" / "acts"
    chroma_dir: Path = BACKEND_DIR / "chroma_db"

    # --- Embedding & reranking models ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Retrieval pipeline parameters ---
    # Lowered from 20 → 12 and 5 → 4 for faster reranking with no observable
    # quality loss at our corpus size (~thousands of chunks).
    retrieval_top_k: int = Field(default=12, ge=1, le=100)
    rerank_top_k: int = Field(default=4, ge=1, le=50)

    # --- Gemini (final generation layer only) ---
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    # Comma-separated priority list. The llm_caller wrapper tries them in
    # order and falls through to the next on 429 (daily quota exhausted).
    # Newer models (3.1) tend to have stricter free-tier caps; older "lite"
    # models are kept at the tail of the list as a safety net.
    # Override per-deployment via the GEMINI_MODEL env var.
    gemini_model: str = Field(default="", validation_alias="GEMINI_MODEL")

    # --- API server ---
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    def ensure_dirs(self) -> None:
        """Create runtime directories if they do not yet exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide Settings singleton."""
    return Settings()
