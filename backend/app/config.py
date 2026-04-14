"""LennyVerse — Configuration."""
import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))
    environment: str = field(default_factory=lambda: os.getenv("ENV", "development"))
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000"
        ).split(",") if o.strip()
    ])

    # Paths
    wiki_path: Path = field(default_factory=lambda: Path(
        os.getenv("WIKI_PATH", str(Path(__file__).parent.parent.parent / "knowledge" / "wiki"))
    ))
    raw_path: Path = field(default_factory=lambda: Path(
        os.getenv("RAW_PATH", str(Path(__file__).parent.parent.parent / "knowledge" / "raw"))
    ))
    schema_path: Path = field(default_factory=lambda: Path(
        os.getenv("SCHEMA_PATH", str(Path(__file__).parent.parent.parent / "knowledge" / "schema.md"))
    ))

    # LLM settings
    compile_model: str = field(default_factory=lambda: os.getenv("COMPILE_MODEL", "claude-sonnet-4-6-20250514"))
    explore_model: str = field(default_factory=lambda: os.getenv("EXPLORE_MODEL", "claude-sonnet-4-6-20250514"))
    max_tokens_compile: int = 4096
    max_tokens_explore: int = 1024
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", "120")))

    # Ollama fallback (when no ANTHROPIC_API_KEY)
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2:3b"))

    # Rate limiting
    rate_limit: str = field(default_factory=lambda: os.getenv("RATE_LIMIT", "10/minute"))

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


config = Config()
