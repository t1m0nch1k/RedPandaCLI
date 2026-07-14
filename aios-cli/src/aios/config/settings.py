from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

import tomlkit
from pydantic import BaseModel

CONFIG_DIR = Path.home() / ".aios"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DB_FILE = CONFIG_DIR / "history.db"
LOG_FILE = CONFIG_DIR / "aios.log"

DEFAULT_CONFIG = """default_provider = "ollama"
default_model = "qwen3:8b"
temperature = 0.2

# ── Local / Self-hosted ──────────────────────────────────────────
[providers.ollama]
base_url = "http://localhost:11434"

[providers.ollama_openai]
api_key = ""
base_url = "http://localhost:11434/v1"

[providers.lmstudio]
base_url = "http://localhost:1234/v1"

[providers.vllm]
base_url = "http://localhost:8000/v1"

[providers.koboldcpp]
base_url = "http://localhost:5001/v1"

[providers.llamacpp]
base_url = "http://localhost:8080/v1"

[providers.tabbyapi]
base_url = "http://localhost:8080/v1"

[providers.localai]
base_url = "http://localhost:8080/v1"

[providers.oobabooga]
base_url = "http://localhost:5000/v1"

[providers.textgen]
base_url = "http://localhost:5000/v1"

# ── Major Cloud Providers ───────────────────────────────────────
[providers.openai]
api_key = ""
base_url = "https://api.openai.com/v1"

[providers.azure]
api_key = ""
base_url = "https://YOUR_RESOURCE.openai.azure.com"

[providers.google]
api_key = ""
base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

[providers.aws_bedrock]
api_key = ""
base_url = "https://bedrock-runtime.YOUR_REGION.amazonaws.com"

[providers.grok]
api_key = ""
base_url = "https://api.x.ai/v1"

[providers.deepseek]
api_key = ""
base_url = "https://api.deepseek.com/v1"

[providers.mistral]
api_key = ""
base_url = "https://api.mistral.ai/v1"

# ── Aggregators / Multi-Model ───────────────────────────────────
[providers.openrouter]
api_key = ""
base_url = "https://openrouter.ai/api/v1"

[providers.groq]
api_key = ""
base_url = "https://api.groq.com/openai/v1"

[providers.together]
api_key = ""
base_url = "https://api.together.xyz/v1"

[providers.fireworks]
api_key = ""
base_url = "https://api.fireworks.ai/inference/v1"

[providers.deepinfra]
api_key = ""
base_url = "https://api.deepinfra.com/v1/openai"

[providers.sambanova]
api_key = ""
base_url = "https://api.sambanova.ai/v1"

[providers.anyscale]
api_key = ""
base_url = "https://api.endpoints.anyscale.com/v1"

[providers.perplexity]
api_key = ""
base_url = "https://api.perplexity.ai"

[providers.github_models]
api_key = ""
base_url = "https://models.inference.ai.azure.com"

[providers.replicate]
api_key = ""
base_url = "https://api.replicate.com/v1"

# ── Niche / Emerging ───────────────────────────────────────────
[providers.cerebras]
api_key = ""
base_url = "https://api.cerebras.ai/v1"

[providers.octoai]
api_key = ""
base_url = "https://text.octoai.run/v1"

[providers.ai21]
api_key = ""
base_url = "https://api.ai21.com/studio/v1"

[providers.cohere]
api_key = ""
base_url = "https://api.cohere.ai/v1"

[providers.huggingface]
api_key = ""
base_url = "https://api-inference.huggingface.co/v1"

[providers.nvidia_nim]
api_key = ""
base_url = "https://integrate.api.nvidia.com/v1"

[providers.aimlapi]
api_key = ""
base_url = "https://api.aimlapi.com/v1"

[providers.novita]
api_key = ""
base_url = "https://api.novita.ai/v3/openai"

[providers.lepton]
api_key = ""
base_url = "https://YOUR_WORKSPACE.lepton.ai/api"

[providers.featherless]
api_key = ""
base_url = "https://api.featherless.ai/v1"

[providers.inferless]
api_key = ""
base_url = "https://api.inferless.com/v1"

[providers.friendli]
api_key = ""
base_url = "https://api.friendli.ai/serverless/v1"

[providers.helion]
api_key = ""
base_url = "https://api.helion.ai/v1"

# ── Git Workflow ─────────────────────────────────────────────────
[git]
auto_commit = false
protected_branches = ["main", "master", "develop"]
secret_scanning = true
commit_prefix = "aios: "
"""


def _resolve_env(value: Any) -> Any:
    """Resolves ${ENV_VAR} or $ENV_VAR patterns in strings."""
    if not isinstance(value, str):
        return value
    
    # Pattern for ${VAR} or $VAR
    pattern = r"\$\{(\w+)\}|\$(\w+)"
    
    def replace(match: re.Match) -> str:
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, match.group(0))
    
    return re.sub(pattern, replace, value)


class ProviderConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""


class MCPServerConfig(BaseModel):
    name: str = ""
    command: str = ""
    args: list[str] = []
    env: dict[str, str] = {}
    transport: str = "stdio"
    url: str = ""


class GitConfig(BaseModel):
    auto_commit: bool = False
    protected_branches: list[str] = ["main", "master", "develop"]
    secret_scanning: bool = True
    commit_prefix: str = "aios: "


class TestConfig(BaseModel):
    auto_test: bool = True
    test_command: str = "pytest"


class Settings(BaseModel):
    default_provider: str = "ollama"
    default_model: str = "qwen3:8b"
    temperature: float = 0.2
    providers: dict[str, ProviderConfig] = {}
    mcp_servers: list[MCPServerConfig] = []
    git: GitConfig = GitConfig()
    testing: TestConfig = TestConfig()

    @classmethod
    def load(cls) -> Settings:
        ensure_config_exists()
        with open(CONFIG_FILE, "rb") as f:
            raw = tomllib.load(f)
        
        # Resolve env vars for top-level settings
        default_provider = _resolve_env(raw.get("default_provider", "ollama"))
        default_model = _resolve_env(raw.get("default_model", "qwen3:8b"))
        temperature = raw.get("temperature", 0.2)

        providers = {}
        for name, cfg in raw.get("providers", {}).items():
            resolved_cfg = {
                k: _resolve_env(v) for k, v in cfg.items()
            }
            providers[name] = ProviderConfig(**resolved_cfg)

        mcp_servers = []
        for cfg in raw.get("mcp", {}).get("servers", []):
            mcp_servers.append(MCPServerConfig(**{k: _resolve_env(v) for k, v in cfg.items()}))

        git_cfg = raw.get("git", {})
        git_config = GitConfig(
            auto_commit=git_cfg.get("auto_commit", False),
            protected_branches=git_cfg.get("protected_branches", ["main", "master", "develop"]),
            secret_scanning=git_cfg.get("secret_scanning", True),
            commit_prefix=git_cfg.get("commit_prefix", "aios: "),
        )
        
        test_cfg = raw.get("testing", {})
        test_config = TestConfig(
            auto_test=test_cfg.get("auto_test", True),
            test_command=test_cfg.get("test_command", "pytest"),
        )
            
        return cls(
            default_provider=default_provider,
            default_model=default_model,
            temperature=temperature,
            providers=providers,
            mcp_servers=mcp_servers,
            git=git_config,
            testing=test_config,
        )


def ensure_config_exists() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG, encoding="utf-8")


def get_settings() -> Settings:
    return Settings.load()


def add_provider_to_config(name: str, base_url: str, api_key: str = "") -> None:
    ensure_config_exists()
    text = CONFIG_FILE.read_text(encoding="utf-8")
    try:
        doc = tomlkit.parse(text)
    except Exception:
        raise ValueError("config.toml is malformed. Please fix it manually.")
    
    if "providers" not in doc:
        doc.add("providers", tomlkit.table())
    
    if name not in doc["providers"]:
        provider_table = tomlkit.table()
        provider_table.add("api_key", api_key)
        provider_table.add("base_url", base_url)
        doc["providers"].add(name, provider_table)
        CONFIG_FILE.write_text(tomlkit.dumps(doc), encoding="utf-8")

def update_default_settings(provider: str | None = None, model: str | None = None) -> None:
    ensure_config_exists()
    text = CONFIG_FILE.read_text(encoding="utf-8")
    try:
        doc = tomlkit.parse(text)
    except Exception:
        raise ValueError("config.toml is malformed. Please fix it manually.")
        
    if provider is not None:
        doc["default_provider"] = provider
    if model is not None:
        doc["default_model"] = model
    CONFIG_FILE.write_text(tomlkit.dumps(doc), encoding="utf-8")

def set_api_key_in_config(provider_name: str, api_key: str) -> None:
    ensure_config_exists()
    text = CONFIG_FILE.read_text(encoding="utf-8")
    try:
        doc = tomlkit.parse(text)
    except Exception:
        raise ValueError("config.toml is malformed. Please fix it manually.")
        
    if "providers" not in doc or provider_name not in doc["providers"]:
        raise ValueError(f"Provider '{provider_name}' not found in config.")
        
    doc["providers"][provider_name]["api_key"] = api_key
    CONFIG_FILE.write_text(tomlkit.dumps(doc), encoding="utf-8")
