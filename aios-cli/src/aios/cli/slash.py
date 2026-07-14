from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text

from aios.config.settings import CONFIG_FILE, add_provider_to_config, get_settings

console = Console()

SlashHandler = Callable[..., str | Text | None]

_COMMANDS: list[dict[str, Any]] = []


def register(
    names: list[str],
    handler: SlashHandler,
    category: str = "General",
    description: str = "",
    usage: str = "",
) -> None:
    for name in names:
        _COMMANDS.append({
            "name": name,
            "handler": handler,
            "category": category,
            "description": description,
            "usage": usage,
        })


def get_commands() -> list[dict[str, Any]]:
    return list(_COMMANDS)


def get_command(name: str) -> dict[str, Any] | None:
    for cmd in _COMMANDS:
        if cmd["name"] == name:
            return cmd
    return None


def get_categories() -> dict[str, list[dict[str, Any]]]:
    cats: dict[str, list[dict[str, Any]]] = {}
    for cmd in _COMMANDS:
        cats.setdefault(cmd["category"], []).append(cmd)
    return cats


# ── Help ────────────────────────────────────────────────────────────

async def _help(_args: list[str]) -> str:
    cats = get_categories()
    lines: list[str] = []
    lines.append("AIOS Commands")
    lines.append("")

    for cat_name in ["Core", "AI", "Git", "Session", "Plugins", "System", "General"]:
        cmds = cats.get(cat_name, [])
        if not cmds:
            continue
        lines.append(f"\n{cat_name}")
        lines.append("-" * 22)
        for c in cmds:
            usage = c.get("usage", "")
            spacer = " " * max(1, 22 - len(c["name"]))
            desc = c["description"]
            if usage:
                lines.append(f"  {c['name']}{spacer}{desc}  [{usage}]")
            else:
                lines.append(f"  {c['name']}{spacer}{desc}")
        lines.append("")

    return "\n".join(lines)


register(["/help", "/?"], _help, "Core", "Show this help")
register(["/exit", "/quit"], lambda a: "EXIT", "Core", "Exit AIOS")
register(["/clear"], lambda a: "CLEAR", "Core", "Clear screen")

# ── AI ──────────────────────────────────────────────────────────────

async def _provider(args: list[str]) -> str:
    if not args:
        return "Usage: /provider <name>\nAvailable: " + ", ".join(
            get_settings().providers.keys()
        )
    settings = get_settings()
    settings.default_provider = args[0]
    return f"Provider switched to [bold]{args[0]}[/bold]"


async def _model(args: list[str]) -> str:
    if not args:
        return "Usage: /model <name>"
    settings = get_settings()
    settings.default_model = args[0]
    return f"Model switched to [bold]{args[0]}[/bold]"


async def _models(_args: list[str]) -> str:
    settings = get_settings()
    names = list(settings.providers.keys())
    return "Available providers:\n" + "\n".join(f"  [bold]{n}[/bold]" for n in names)


async def _tools(_args: list[str]) -> str:
    from aios.tools.registry import ToolRegistry
    reg = ToolRegistry()
    lines = [f"  [bold]{t.name}[/bold] — {t.description}" for t in reg.list()]
    return "Registered tools:\n" + "\n".join(lines)


async def _add_provider(args: list[str]) -> str:
    if len(args) < 2:
        return "Usage: /add-provider <name> <endpoint_url> [api_key]"
    name, endpoint = args[0], args[1]
    api_key = args[2] if len(args) > 2 else ""
    settings = get_settings()
    if name in settings.providers:
        return f"Provider '{name}' already exists."
    add_provider_to_config(name, endpoint, api_key)
    return f"Provider [bold]{name}[/bold] added: {endpoint}"


register(["/provider"], _provider, "AI", "Switch provider", "/provider <name>")
register(["/model"], _model, "AI", "Switch model", "/model <name>")
register(["/models"], _models, "AI", "List providers")
register(["/tools"], _tools, "AI", "List registered tools")
register(["/add-provider"], _add_provider, "AI", "Add custom provider", "/add-provider <name> <url> [key]")
register(["/key"], lambda a: "", "AI", "Set API Key for current provider")

# ── Git ─────────────────────────────────────────────────────────────

async def _git(args: list[str]) -> str:
    from aios.config.settings import GitConfig
    from aios.tools.git import GitTool

    gt = GitTool(git_config=GitConfig())

    if not args:
        out, err, _ = await _run_git_raw(["status", "--short", "--branch"])
        return out if not err else f"Error: {err}"

    action = args[0]

    if action == "status":
        r = await gt.run(action="status")
    elif action == "diff":
        r = await gt.run(action="diff")
    elif action == "commit":
        msg = " ".join(args[1:]) if len(args) > 1 else ""
        r = await gt.run(action="commit", message=msg, paths=["*"])
    elif action in ("smart-commit", "sc"):
        r = await gt.run(action="smart_commit")
    elif action == "log":
        count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        r = await gt.run(action="log", count=count)
    elif action == "branch":
        r = await gt.run(action="branch", branch_action="list")
    elif action == "push":
        r = await gt.run(action="push")
    elif action == "pull":
        r = await gt.run(action="pull")
    else:
        return f"Unknown git subcommand: {action}"

    if r.success:
        return r.output or "Done"
    return f"Error: {r.error}"


async def _run_git_raw(args: list[str]) -> tuple[str, str, int]:
    import asyncio
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace"), proc.returncode or 0


register(
    ["/git"], _git, "Git",
    "Git operations: status, diff, commit, smart-commit, log, branch, push, pull",
    "/git <status|diff|commit msg|sc|log [n]|branch|push|pull>",
)

# ── Session ─────────────────────────────────────────────────────────

async def _retry(_args: list[str]) -> str:
    return "RETRY"


async def _save(args: list[str]) -> str:
    from aios.memory.history import history_store
    name = args[0] if args else "checkpoint"
    path = Path.home() / ".aios" / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    out = path / f"{name}.json"
    data = history_store.recent_conversations(limit=100)
    import json
    out.write_text(json.dumps(data, indent=2, default=str))
    return f"Session saved to [bold]{out}[/bold]"


async def _load(args: list[str]) -> str:
    if not args:
        return "Usage: /load <name>"
    path = Path.home() / ".aios" / "sessions" / f"{args[0]}.json"
    if not path.exists():
        return f"Session [bold]{args[0]}[/bold] not found"
    return f"Session [bold]{args[0]}[/bold] loaded"


async def _compact(_args: list[str]) -> str:
    return "COMPACT"


register(
    ["/retry", "/r"], _retry, "Session",
    "Re-run the last assistant response",
)
register(["/save"], _save, "Session", "Save session checkpoint", "/save <name>")
register(["/load"], _load, "Session", "Load session checkpoint", "/load <name>")
register(["/compact"], _compact, "Session", "Compress conversation context")

# ── Plugins ─────────────────────────────────────────────────────────

async def _plugins(_args: list[str]) -> str:
    from aios.plugins.config import get_installed_plugins
    from aios.plugins.loader import LOCAL_PLUGIN_DIRS

    local = []
    for d in LOCAL_PLUGIN_DIRS:
        if d.exists():
            for child in sorted(d.iterdir()):
                if child.is_dir() and (child / "plugin.py").exists():
                    local.append(child.name)

    installed = get_installed_plugins()
    installed_names = {p["name"] for p in installed}

    lines = ["[bold]Plugins[/bold]\n"]
    for name in sorted(set(local) | installed_names):
        marker = "[green]\u2713[/green]" if name in installed_names else "[dim]local[/dim]"
        lines.append(f"  {marker} {name}")
    if not local and not installed:
        lines.append("  [dim]No plugins[/dim]")
    return "\n".join(lines)


register(
    ["/plugins", "/plugin"], _plugins, "Plugins",
    "List installed and available plugins",
)

# ── System ──────────────────────────────────────────────────────────

async def _config(_args: list[str]) -> str:
    return CONFIG_FILE.read_text(encoding="utf-8")


async def _doctor(_args: list[str]) -> str:
    settings = get_settings()
    import platform
    lines = [
        f"Python: {platform.python_version()}",
        f"Config: {CONFIG_FILE}",
        f"Provider: {settings.default_provider}",
        f"Model: {settings.default_model}",
    ]
    return "\n".join(lines)


async def _version(_args: list[str]) -> str:
    from aios import __version__
    return f"AIOS CLI v{__version__}"


register(["/config"], _config, "System", "Show config")
register(["/doctor"], _doctor, "System", "Diagnose AIOS")
register(["/version"], _version, "System", "Show version")
register(["/logs"], lambda a: "OPEN_LOGS", "System", "Open log file")

# ── Dispatch ────────────────────────────────────────────────────────

async def dispatch_slash_command(text: str) -> str | Text | None:
    text = text.strip()
    if not text:
        return None
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []

    for entry in _COMMANDS:
        if entry["name"] == cmd:
            handler = entry["handler"]
            result = handler(args)
            if hasattr(result, "__await__"):
                result = await result
            return result

    return None


async def dispatch_slash_with_action(text: str) -> tuple[str, str | Text] | None:
    result = await dispatch_slash_command(text)
    if result is None:
        return None

    action_map = {
        "EXIT": "exit",
        "CLEAR": "clear",
        "RETRY": "retry",
        "COMPACT": "compact",
        "OPEN_LOGS": "open_logs",
    }
    action = action_map.get(str(result))
    if action:
        return (action, result)

    return ("message", result)


def get_available_commands() -> list[str]:
    return [c["name"] for c in _COMMANDS]
