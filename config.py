"""Загрузка настроек пайплайна.

.env         — авторизация и подключение (секреты, параметры окружения)
config.yaml  — модель, параметры генерации, промпты, тулы
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# SDK gigachat сам читает переменные GIGACHAT_* из окружения, и пустая строка
# (например, GIGACHAT_BASE_URL=) перебивает его дефолт — убираем пустые значения.
for _name in [n for n, v in os.environ.items() if n.startswith("GIGACHAT_") and not v.strip()]:
    del os.environ[_name]


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, "").strip()
    return value or default


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class AuthSettings:
    """Параметры авторизации и подключения из .env."""

    credentials: str | None = field(default_factory=lambda: _env("GIGACHAT_CREDENTIALS"))
    scope: str = field(default_factory=lambda: _env("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"))
    verify_ssl_certs: bool = field(default_factory=lambda: _env_bool("GIGACHAT_VERIFY_SSL_CERTS"))
    ca_bundle_file: str | None = field(default_factory=lambda: _env("GIGACHAT_CA_BUNDLE_FILE"))
    base_url: str | None = field(default_factory=lambda: _env("GIGACHAT_BASE_URL"))


@dataclass
class ModelSettings:
    name: str = "GigaChat-2"
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    repetition_penalty: float | None = None
    profanity_check: bool | None = None
    streaming: bool | None = None
    timeout: float | None = None


@dataclass
class Settings:
    auth: AuthSettings
    model: ModelSettings
    system_prompt: str | None
    max_tool_iterations: int
    tools: list[str]
    tool_schemas_dir: Path

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "Settings":
        path = Path(config_path or _env("CONFIG_PATH") or BASE_DIR / "config.yaml")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        model_cfg = data.get("model") or {}
        unknown = set(model_cfg) - set(ModelSettings.__dataclass_fields__)
        if unknown:
            raise ValueError(f"Неизвестные параметры в секции model: {sorted(unknown)}")

        prompts_cfg = data.get("prompts") or {}
        system_prompt = None
        if prompts_cfg.get("system"):
            prompt_path = path.parent / prompts_cfg["system"]
            system_prompt = prompt_path.read_text(encoding="utf-8").strip() or None

        pipeline_cfg = data.get("pipeline") or {}
        return cls(
            auth=AuthSettings(),
            model=ModelSettings(**model_cfg),
            system_prompt=system_prompt,
            max_tool_iterations=int(pipeline_cfg.get("max_tool_iterations", 5)),
            tools=list(data.get("tools") or []),
            tool_schemas_dir=path.parent / data.get("tool_schemas_dir", "schemas"),
        )

    def gigachat_kwargs(self) -> dict:
        """Параметры для конструктора GigaChat; незаданные (None) не передаются,
        чтобы сработали дефолты библиотеки."""
        kwargs = {
            "credentials": self.auth.credentials,
            "scope": self.auth.scope,
            "verify_ssl_certs": self.auth.verify_ssl_certs,
            "ca_bundle_file": self.auth.ca_bundle_file,
            "base_url": self.auth.base_url,
            "model": self.model.name,
            "temperature": self.model.temperature,
            "top_p": self.model.top_p,
            "max_tokens": self.model.max_tokens,
            "repetition_penalty": self.model.repetition_penalty,
            "profanity_check": self.model.profanity_check,
            "streaming": self.model.streaming,
            "timeout": self.model.timeout,
        }
        return {k: v for k, v in kwargs.items() if v is not None}
