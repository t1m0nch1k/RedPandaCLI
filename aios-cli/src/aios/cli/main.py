from __future__ import annotations

import asyncio
import json
import platform
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from aios import __version__
from aios.cli.branding import RUST, render_dashboard, render_session_id
from aios.config.settings import add_provider_to_config, get_settings
from aios.core.models import Conversation, Role, StreamChunk
from aios.executor.agent import Agent
from aios.executor.coding_agent import CodingAgent
from aios.memory.history import history_store
from aios.providers.plugins import (
    PROVIDER_PLUGIN_DIR,
    discover_and_register_provider_plugins,
)
from aios.providers.registry import build_provider, list_provider_names, list_registered_providers
from aios.tools.registry import ToolRegistry

app = typer.Typer(help="AIOS CLI — foundation of the AIOS ecosystem")
console = Console()


def _build_registry(settings=None) -> ToolRegistry:
    """Build a fresh ToolRegistry scoped to the current working directory."""
    return ToolRegistry(git_config=settings.git if settings else None)


def get_provider_and_model(provider: str | None, model: str | None):
    discover_and_register_provider_plugins()
    settings = get_settings()
    provider_name = provider or settings.default_provider
    model_name = model or settings.default_model
    return build_provider(provider_name, model_name, settings), settings, provider_name, model_name


def _git_config(settings) -> dict:
    return settings.git


def _mcp_config(settings) -> list[dict[str, Any]]:
    return [s.model_dump() for s in settings.mcp_servers]


def _print_dashboard(provider_name: str, model_name: str, tool_registry: ToolRegistry) -> None:
    settings = get_settings()
    console.print(
        render_dashboard(
            version=__version__,
            provider=provider_name,
            model=model_name,
            tools=[t.name for t in tool_registry.list()],
            providers=list_provider_names(settings),
            session_id=render_session_id(),
        )
    )


async def _stream_reply(conversation: Conversation, provider_obj) -> str:
    full_text = ""
    with console.status("[bold cyan]thinking...", spinner="dots"):
        pass
    async for chunk in provider_obj.stream(conversation.messages, temperature=0.2):
        console.print(chunk, end="")
        full_text += chunk
    console.print()
    return full_text


async def _ensure_model_available(provider_obj, provider_name: str, model_name: str) -> bool:
    if provider_name != "ollama":
        return True
    try:
        ok = await provider_obj.has_model(model_name)
    except httpx.HTTPError:
        console.print(f"[red]Cannot reach Ollama at {provider_obj.base_url}. Is it running?")
        return False
    if not ok:
        console.print(f"[yellow]Model '{model_name}' not found locally. Run: ollama pull {model_name}")
    return ok


async def _handle_prompt(text: str, provider: str | None, model: str | None) -> None:
    provider_obj, settings, provider_name, model_name = get_provider_and_model(provider, model)
    if not await _ensure_model_available(provider_obj, provider_name, model_name):
        return

    conversation = Conversation(provider=provider_name, model=model_name)
    conversation.add(Role.USER, text)

    agent = Agent(provider_obj, _build_registry(settings), git_config=settings.git)
    reply = await agent.run(conversation)
    console.print(Panel(reply, title="AIOS Agent", border_style="cyan"))


def _build_prompt_session(history_file: str):
    from prompt_toolkit import PromptSession
    from prompt_toolkit.application import get_app
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.filters import Condition, has_completions
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings

    from aios.cli.slash import get_available_commands
    
    # sentence=True ensures it matches the entire string from the start, 
    # so `/e` matches `/exit`.
    slash_completer = WordCompleter(get_available_commands(), ignore_case=True, sentence=True)
    kb = KeyBindings()
    
    @Condition
    def is_slash_command():
        return get_app().current_buffer.text.startswith('/')
    
    @kb.add('down', filter=is_slash_command & has_completions)
    def _(event):
        event.current_buffer.complete_next()
        
    @kb.add('up', filter=is_slash_command & has_completions)
    def _(event):
        event.current_buffer.complete_previous()
    
    @kb.add('escape', 'enter')
    def _(event):
        event.current_buffer.insert_text('\n')
        
    @kb.add('enter')
    def _(event):
        event.current_buffer.validate_and_handle()
        
    return PromptSession(
        history=FileHistory(history_file),
        completer=slash_completer,
        auto_suggest=AutoSuggestFromHistory(),
        key_bindings=kb,
        complete_while_typing=True,
        multiline=True,
    )


@app.command()
def ask(
    prompt: str,
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
) -> None:
    asyncio.run(_handle_prompt(prompt, provider, model))


async def _run_agent_loop(
    conversation: Conversation,
    prompt_html: str,
    history_file_name: str,
    agent_factory: Callable[[Callable], Agent],
    use_live_markdown: bool = False,
) -> None:
    from prompt_toolkit.formatted_text import HTML
    from rich.live import Live

    from aios.config.settings import CONFIG_DIR

    session = _build_prompt_session(str(CONFIG_DIR / history_file_name))

    while True:
        try:
            text = await session.prompt_async(HTML(prompt_html))
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        if not text.strip():
            continue

        if text.strip().lower() in {"exit", "quit"}:
            break

        if text.strip().startswith("/"):
            from aios.cli.slash import dispatch_slash_command
            reply = await dispatch_slash_command(text)
            if reply:
                console.print(Panel(reply, title="AIOS System", border_style="blue"))
            else:
                console.print(f"[red]Unknown command: {text}[/red]")
            continue

        user_msg = conversation.add(Role.USER, text)
        history_store.add_message(conversation.id, user_msg.id, "user", text)

        tool_status = None

        def on_state(state):
            nonlocal tool_status
            from aios.runtime.models import ExecutionState

            if tool_status:
                tool_status.stop()
                tool_status = None
            if state == ExecutionState.TOOL:
                tool_status = console.status("[bold yellow]Executing tool...[/bold yellow]", spinner="bouncingBar")
                tool_status.start()

        agent = agent_factory(on_state)

        async def _run_agent_with_stream(stream_callback):
            try:
                return await agent.run(conversation, stream_callback=stream_callback)
            except asyncio.CancelledError:
                return "<CANCELLED>"
            except Exception as e:
                console.print(f"\n[red]Error:[/red] {e}")
                import logging
                logging.exception("Agent run failed")
                return None
            finally:
                if tool_status:
                    tool_status.stop()

        if use_live_markdown:
            current_text = ""
            with Live(Markdown(""), console=console, refresh_per_second=15, vertical_overflow="visible") as live:
                async def on_stream(chunk: StreamChunk) -> None:
                    nonlocal current_text
                    if chunk.type == "content":
                        current_text += chunk.content
                        live.update(Markdown(current_text))

                reply = await _run_agent_with_stream(on_stream)
                
                if reply == "<CANCELLED>":
                    current_text += "\n\n> **Generation cancelled.**"
                    live.update(Markdown(current_text))
                    reply = ""
                elif reply and not current_text:
                    console.print(Markdown(reply))
        else:
            async def on_stream(chunk: StreamChunk) -> None:
                if chunk.type == "content":
                    console.print(chunk.content, end="")

            reply = await _run_agent_with_stream(on_stream)
            if reply == "<CANCELLED>":
                console.print("\n[yellow]Generation cancelled.[/yellow]")
                reply = ""
            elif reply:
                console.print()

        if reply:
            assistant_msg = conversation.add(Role.ASSISTANT, reply)
            history_store.add_message(conversation.id, assistant_msg.id, "assistant", reply)


@app.command()
def chat(
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
) -> None:
    async def loop() -> None:
        provider_obj, settings, provider_name, model_name = get_provider_and_model(provider, model)
        tool_registry = _build_registry()
        _print_dashboard(provider_name, model_name, tool_registry)
        if not await _ensure_model_available(provider_obj, provider_name, model_name):
            return
        conversation = Conversation(provider=provider_name, model=model_name)
        history_store.ensure_conversation(conversation.id, provider_name, model_name)

        def agent_factory(on_state):
            return Agent(
                provider_obj, 
                tool_registry, 
                mcp_servers=_mcp_config(settings), 
                git_config=settings.git, 
                state_callback=on_state
            )

        await _run_agent_loop(
            conversation=conversation,
            prompt_html='<b>🐾 </b><style color="#d1491f"><b>> </b></style>',
            history_file_name=".chat_history",
            agent_factory=agent_factory,
            use_live_markdown=True,
        )

    asyncio.run(loop())


async def _confirm_action(tool_name: str, args: dict[str, Any]) -> bool:
    """Callback to ask the user for confirmation before executing a dangerous action."""
    from rich.json import JSON
    
    safe_args = {k: (v[:200] + "... [truncated]" if isinstance(v, str) and len(v) > 200 else v) for k, v in args.items()}
    args_str = json.dumps(safe_args, ensure_ascii=False, indent=2)
    
    console.print(f"\n[bold yellow]⚠️  Action Request:[/bold yellow] {tool_name}")
    console.print(JSON(args_str))
    
    choice = console.input("[bold red]Confirm execution? [Y/n]: [/bold red]")
    return choice.strip().lower() in {"y", "", "yes"}


@app.command()
def code(
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
) -> None:
    async def loop() -> None:
        provider_obj, settings, provider_name, model_name = get_provider_and_model(provider, model)
        tool_registry = _build_registry(settings)
        _print_dashboard(provider_name, model_name, tool_registry)
        if not await _ensure_model_available(provider_obj, provider_name, model_name):
            return
        conversation = Conversation(provider=provider_name, model=model_name)
        conversation.add(
            Role.SYSTEM,
            "You are an expert coding assistant. Answer with precise, runnable code and short explanations.",
        )
        history_store.ensure_conversation(conversation.id, provider_name, model_name)

        def agent_factory(on_state):
            return CodingAgent(
                provider_obj, 
                tool_registry, 
                confirmation_callback=_confirm_action, 
                state_callback=on_state,
                mcp_servers=_mcp_config(settings), 
                git_config=settings.git
            )

        await _run_agent_loop(
            conversation=conversation,
            prompt_html='<b>🐾 </b><style color="#d1491f"><b>code> </b></style>',
            history_file_name=".code_history",
            agent_factory=agent_factory,
            use_live_markdown=False,
        )

    asyncio.run(loop())


@app.command()
def doctor() -> None:
    settings = get_settings()
    table = Table(title="AIOS Doctor", border_style=RUST, header_style=f"bold {RUST}")
    table.add_column("Check")
    table.add_column("Status")

    table.add_row("Python", platform.python_version())
    table.add_row("Config file", str(settings.default_provider is not None))
    table.add_row("Default provider", settings.default_provider)
    table.add_row("Default model", settings.default_model)

    async def check_provider() -> tuple[str, str]:
        try:
            provider_obj, *_ = get_provider_and_model(None, None)
            ok = await provider_obj.health_check()
            if not ok:
                return "[red]unreachable", "[red]unknown"
            model_ok = await provider_obj.has_model(settings.default_model)
            model_status = "[green]installed" if model_ok else "[yellow]not found"
            return "[green]reachable", model_status
        except Exception as exc:
            return f"[red]error: {exc}", "[red]unknown"

    status, model_status = asyncio.run(check_provider())
    table.add_row("Provider health", status)
    table.add_row("Default model available", model_status)

    if settings.default_provider == "ollama" and "not found" in model_status:
        console.print(
            f"[yellow]Model '{settings.default_model}' not installed. "
            f"Run: ollama pull {settings.default_model}"
        )

    console.print(table)


@app.command(name="config")
def config_cmd(
    show: bool = typer.Option(False, "--show"),
    set_default_provider: str = typer.Option(None, "--set-provider"),
    set_default_model: str = typer.Option(None, "--set-model"),
) -> None:
    from aios.config.settings import CONFIG_FILE, ensure_config_exists, update_default_settings

    ensure_config_exists()

    if set_default_provider or set_default_model:
        try:
            update_default_settings(provider=set_default_provider, model=set_default_model)
            console.print("[green]Config updated.[/green]")
        except Exception as e:
            console.print(f"[red]Error updating config: {e}[/red]")
        return

    console.print(Markdown(f"```toml\n{CONFIG_FILE.read_text(encoding='utf-8')}\n```"))


@app.command()
def history(limit: int = typer.Option(20, "--limit", "-n")) -> None:
    rows = history_store.recent_conversations(limit=limit)
    table = Table(title="Conversation History", border_style=RUST, header_style=f"bold {RUST}")
    table.add_column("ID")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Created")

    for row in rows:
        table.add_row(row["id"][:8], row["provider"] or "-", row["model"] or "-", str(row["created_at"]))

    console.print(table)


@app.command()
def tools() -> None:
    table = Table(title="Registered Tools", border_style=RUST, header_style=f"bold {RUST}")
    table.add_column("Name")
    table.add_column("Description")

    for tool in _build_registry().list():
        table.add_row(tool.name, tool.description)

    console.print(table)


@app.command(name="plugin-list")
def plugin_list() -> None:
    """List installed plugins."""
    from aios.plugins.config import get_installed_plugins
    from aios.plugins.loader import LOCAL_PLUGIN_DIRS

    local_found = []
    for d in LOCAL_PLUGIN_DIRS:
        if d.exists():
            for child in sorted(d.iterdir()):
                if child.is_dir() and (child / "plugin.py").exists():
                    local_found.append(child.name)

    installed = get_installed_plugins()
    installed_names = {p["name"] for p in installed}

    table = Table(title="AIOS Plugins", border_style=RUST, header_style=f"bold {RUST}")
    table.add_column("Name")
    table.add_column("Source")
    table.add_column("Type")

    for name in sorted(set(local_found) | installed_names):
        source = "installed" if name in installed_names else "local"
        source_url = next((p["source"] for p in installed if p["name"] == name), "local")
        table.add_row(name, source_url, "dir" if name in local_found else "installed")

    if not local_found and not installed:
        console.print("[dim]No plugins installed. Use `aios plugin-install <name|url>` to add one.")
        return

    console.print(table)


@app.command(name="plugin-install")
def plugin_install(
    source: str = typer.Argument(..., help="Git URL, local path, or catalog name"),
) -> None:
    """Install a plugin from git URL, local path, or catalog."""
    from aios.plugins.catalog import find_in_catalog, get_catalog_entries
    from aios.plugins.loader import install_from_git, install_from_path

    path = Path(source)
    if path.exists():
        result = install_from_path(source)
    elif source.startswith(("http://", "https://", "git@", "git://")):
        result = install_from_git(source)
    else:
        entry = find_in_catalog(source)
        if entry:
            result = install_from_git(entry["repo"], name=source)
        else:
            entries = get_catalog_entries()
            names = ", ".join(e["name"] for e in entries)
            console.print(f"[red]Unknown plugin '{source}'.\nAvailable: {names}")
            return

    if result:
        console.print(f"[green]Plugin installed at {result}")
    else:
        console.print("[red]Failed to install plugin.")


@app.command(name="plugin-remove")
def plugin_remove(
    name: str = typer.Argument(..., help="Plugin name to remove"),
) -> None:
    """Remove an installed plugin."""
    from aios.plugins.config import PLUGINS_INSTALL_DIR

    target = PLUGINS_INSTALL_DIR / name
    if not target.exists():
        console.print(f"[red]Plugin '{name}' is not installed.")
        return

    import shutil
    shutil.rmtree(target)
    console.print(f"[green]Removed plugin '{name}'.")


@app.command(name="plugin-enable")
def plugin_enable(
    name: str = typer.Argument(..., help="Plugin name to enable"),
) -> None:
    """Enable a plugin."""
    from aios.plugins.config import set_plugin_enabled
    set_plugin_enabled(name, True)
    console.print(f"[green]Enabled plugin '{name}'. Restart to activate.")


@app.command(name="plugin-disable")
def plugin_disable(
    name: str = typer.Argument(..., help="Plugin name to disable"),
) -> None:
    """Disable a plugin."""
    from aios.plugins.config import set_plugin_enabled
    set_plugin_enabled(name, False)
    console.print(f"[yellow]Disabled plugin '{name}'.")


PROVIDER_HELP = """\
[name]  Register or install a new provider.

[green]Examples:[/green]
  aios provider-register my-provider --class my_module.MyProvider   Register a provider class
  aios provider-install anthropic              Install from catalog
  aios provider-install https://...             Install from git
  aios provider-remove anthropic               Remove installed provider
"""


@app.command(name="provider-list")
def provider_list() -> None:
    """List registered provider plugins."""
    registered = list_registered_providers()

    table = Table(title="Registered Providers", border_style=RUST, header_style=f"bold {RUST}")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Source")

    for name in sorted(registered):
        table.add_row(name, "plugin", "built-in / custom")

    if PROVIDER_PLUGIN_DIR.exists():
        for child in sorted(PROVIDER_PLUGIN_DIR.iterdir()):
            if child.is_dir() and (child / "plugin.py").exists():
                if child.name not in registered:
                    table.add_row(child.name, "plugin", "installed (not loaded)")

    if not registered:
        table.add_row("(none)", "", "")

    console.print(table)


@app.command(name="provider-install")
def provider_install(
    source: str = typer.Argument(..., help="Git URL, local path, or catalog name"),
) -> None:
    """Install a provider plugin from git URL, local path, or catalog."""
    from aios.providers.catalog import find_in_catalog, get_catalog_entries
    from aios.providers.plugins import install_provider_plugin_from_git, install_provider_plugin_from_path

    path = Path(source)
    if path.exists():
        result = install_provider_plugin_from_path(source)
    elif source.startswith(("http://", "https://", "git@", "git://")):
        result = install_provider_plugin_from_git(source)
    else:
        entry = find_in_catalog(source)
        if entry:
            result = install_provider_plugin_from_git(entry["repo"], name=source)
        else:
            entries = get_catalog_entries()
            names = ", ".join(e["name"] for e in entries)
            console.print(f"[red]Unknown provider '{source}'.\nAvailable: {names}")
            return

    if result:
        console.print(f"[green]Provider plugin installed at {result}")
        console.print("[yellow]Restart AIOS to load the new provider.")
    else:
        console.print("[red]Failed to install provider plugin.")


@app.command(name="provider-remove")
def provider_remove(
    name: str = typer.Argument(..., help="Provider plugin name to remove"),
) -> None:
    """Remove an installed provider plugin."""
    target = PROVIDER_PLUGIN_DIR / name
    if not target.exists():
        console.print(f"[red]Provider plugin '{name}' is not installed at {target}.")
        return

    import shutil
    shutil.rmtree(target)
    console.print(f"[green]Removed provider plugin '{name}'.")


@app.command(name="provider-register")
def provider_register(
    name: str = typer.Argument(..., help="Provider name"),
    url: str = typer.Option("", "--url", "-u", help="Base URL"),
    api_key: str = typer.Option("", "--api-key", "-k", help="API key (or set env var)"),
    set_default: bool = typer.Option(False, "--default", "-d", help="Set as default provider"),
) -> None:
    """Register an OpenAI-compatible provider in the config file."""
    if not url:
        console.print("[red]--url is required.")
        raise typer.Exit(code=1)

    add_provider_to_config(name, url, api_key)

    if set_default:
        from aios.config.settings import update_default_settings
        try:
            update_default_settings(provider=name)
        except Exception as e:
            console.print(f"[red]Error setting default provider: {e}[/red]")

    discover_and_register_provider_plugins()
    console.print(f"[green]Registered provider '{name}' → {url}")
    if set_default:
        console.print("[green]Set as default provider.[/green]")


@app.command()
def models(
    provider: str = typer.Option(None, "--provider", "-p"),
    local: bool = typer.Option(False, "--local", help="Show only Ollama-installed models"),
) -> None:
    async def fetch() -> list[str]:
        provider_obj, *_ = get_provider_and_model(provider or ("ollama" if local else None), "")
        return await provider_obj.list_models()

    try:
        names = asyncio.run(fetch())
    except httpx.HTTPError as exc:
        console.print(f"[red]Failed to fetch models: {exc}")
        raise typer.Exit(code=1) from exc

    table_title = "Installed Ollama Models" if local else "Available Models"
    table = Table(title=table_title, border_style=RUST, header_style=f"bold {RUST}")
    table.add_column("Model")
    for name in names:
        table.add_row(name)

    console.print(table)


@app.command()
def version() -> None:
    console.print(f"AIOS CLI v{__version__}")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    provider: str = typer.Option(None, "--provider", "-p", help="Provider to use"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging"),
) -> None:
    import logging
    from pathlib import Path

    from aios.config.settings import CONFIG_DIR, LOG_FILE
    
    log_level = logging.DEBUG if verbose else logging.INFO
    global_log_file = CONFIG_DIR / "debug.log" if verbose else LOG_FILE
    
    # Ensure local project log directory exists
    local_log_dir = Path.cwd() / ".aios"
    local_log_dir.mkdir(parents=True, exist_ok=True)
    local_log_file = local_log_dir / "debug.log" if verbose else local_log_dir / "aios.log"
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    # Global handler
    global_handler = logging.FileHandler(global_log_file, encoding="utf-8")
    global_handler.setFormatter(formatter)
    logger.addHandler(global_handler)
    
    # Local project handler
    local_handler = logging.FileHandler(local_log_file, encoding="utf-8")
    local_handler.setFormatter(formatter)
    logger.addHandler(local_handler)
    
    logger = logging.getLogger("aios")
    logger.info(f"--- Starting AIOS CLI (provider={provider}, model={model}) ---")
    
    if verbose:
        console.print(f"[dim]Verbose logging enabled: {log_file}[/dim]")

    if ctx.invoked_subcommand is None:
        from aios.cli.tui import AIOS_TUI

        settings = get_settings()
        p_name = provider or settings.default_provider
        m_name = model or settings.default_model
        AIOS_TUI(provider_name=p_name, model_name=m_name).run()


@app.command()
def tui(
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
) -> None:
    """Launch the Textual TUI interface."""
    from aios.cli.tui import AIOS_TUI

    settings = get_settings()
    p_name = provider or settings.default_provider
    m_name = model or settings.default_model
    AIOS_TUI(provider_name=p_name, model_name=m_name).run()


@app.command()
def init(
    name: str = typer.Argument("", help="Project name"),
    template: str = typer.Option("python-package", "--template", "-t", help="Template name"),
    dir: str = typer.Option(None, "--dir", "-d", help="Output directory (default: ./<name>)"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing directory"),
    list_templates: bool = typer.Option(False, "--list", "-l", help="List available templates"),
) -> None:
    """Scaffold a new project from a template."""
    from aios.scaffold.engine import ScaffoldEngine

    engine = ScaffoldEngine()

    if list_templates:
        table = Table(title="Available Templates", border_style=RUST, header_style=f"bold {RUST}")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Source")
        for t in engine.list_templates():
            table.add_row(t.name, t.description, t.source)
        console.print(table)
        return

    if not name:
        console.print("[red]Error: NAME is required. Use --list to see available templates.")
        raise typer.Exit(code=1)

    dest = Path(dir or ".") / name
    if dest.exists() and not force:
        console.print(f"[red]Directory '{dest}' already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    info = engine.get_template(template)
    if info is None:
        available = ", ".join(t.name for t in engine.list_templates())
        console.print(f"[red]Template '{template}' not found. Available: {available}")
        raise typer.Exit(code=1)

    variables = {
        "project_name": name.replace("-", "_").replace(" ", "_"),
        "plugin_name": name.replace("-", "_").replace(" ", "_"),
        "description": f"{name} project",
        "author": "AIOS User",
    }

    result = engine.scaffold(template, dest, variables, force=force)
    if result == -2:
        console.print(f"[red]Template '{template}' not found.")
    elif result == -1:
        console.print(f"[red]Directory '{dest}' already exists.")
    elif result > 0:
        console.print(f"[green]Scaffolded {result} files in {dest}")
        console.print(f"\n[bold]Next:[/bold] cd {dest}")
    else:
        console.print("[yellow]No files created.")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
