from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Input, OptionList, Static

from aios.cli.branding import CREAM, RUST
from aios.config.settings import CONFIG_FILE, get_settings
from aios.memory.history import history_store
from aios.providers.registry import build_provider
from aios.tools.registry import ToolRegistry


class HelpScreen(ModalScreen):
    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help_container {
        width: 52;
        height: auto;
        max-height: 80%;
        background: #1a1d23;
        border: thick $accent;
        padding: 1 2;
    }
    #help_title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    .section-title {
        text-style: bold;
        color: $text;
        padding-top: 1;
    }
    .cmd {
        color: $accent;
    }
    .desc {
        color: $text-muted;
    }
    #close_help {
        dock: bottom;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        SECTIONS = [
            ("Core", [
                ("/help", "Show help"),
                ("/exit", "Exit AIOS"),
                ("/clear", "Clear screen"),
                ("/history", "Show history"),
            ]),
            ("AI", [
                ("/provider", "Switch provider"),
                ("/model", "Switch model"),
                ("/models", "List models"),
                ("/tools", "List tools"),
                ("/add-provider", "Add custom provider"),
            ]),
            ("System", [
                ("/doctor", "Diagnose AIOS"),
                ("/config", "Show config"),
                ("/version", "Version info"),
            ]),
        ]
        with Container(id="help_container"):
            yield Static("\U0001f98a AIOS Help", id="help_title")
            with ScrollableContainer():
                for title, cmds in SECTIONS:
                    yield Static(f"\u2500\u2500 {title} \u2500\u2500", classes="section-title")
                    for cmd, desc in cmds:
                        yield Static(f"  [{RUST}]{cmd}[/{RUST}]  [dim]{desc}[/dim]")
                    yield Static("")
            yield Button("Close", variant="primary", id="close_help")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()


class ToolsScreen(ModalScreen):
    CSS = """
    ToolsScreen {
        align: center middle;
    }
    #tools_container {
        width: 60;
        height: auto;
        max-height: 80%;
        background: #1a1d23;
        border: thick $accent;
        padding: 1 2;
    }
    #tools_title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    #close_tools {
        dock: bottom;
        margin-top: 1;
    }
    """

    def __init__(self, registry: ToolRegistry, **kwargs) -> None:
        super().__init__(**kwargs)
        self._registry = registry

    def compose(self) -> ComposeResult:
        with Container(id="tools_container"):
            yield Static("\U0001f527 Registered Tools", id="tools_title")
            with ScrollableContainer():
                tools = self._registry.list()
                if not tools:
                    yield Static("[dim]No tools registered.[/dim]")
                else:
                    for tool in tools:
                        yield Static(f"  [bold {RUST}]{tool.name}[/bold {RUST}]")
                        yield Static(f"       {tool.description}")
                        yield Static("")
            yield Button("Close", variant="primary", id="close_tools")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()


class HistoryScreen(ModalScreen):
    CSS = """
    HistoryScreen {
        align: center middle;
    }
    #history_container {
        width: 70;
        height: auto;
        max-height: 80%;
        background: #1a1d23;
        border: thick $accent;
        padding: 1 2;
    }
    #history_title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    #close_history {
        dock: bottom;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="history_container"):
            yield Static("\U0001f4dc Conversation History", id="history_title")
            with ScrollableContainer():
                rows = history_store.recent_conversations(limit=20)
                if not rows:
                    yield Static("  [dim]No conversations yet.[/dim]")
                else:
                    for row in rows:
                        conv_id = row["id"][:8]
                        provider = row["provider"] or "-"
                        model = row["model"] or "-"
                        ts = row["created_at"]
                        yield Static(
                            f"  [dim]{conv_id}[/dim]  [{RUST}]{provider}[/{RUST}]  "
                            f"[{CREAM}]{model}[/{CREAM}]  [dim]{ts}[/dim]"
                        )
                yield Static("")
            yield Button("Close", variant="primary", id="close_history")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()


class ConfigScreen(ModalScreen):
    CSS = """
    ConfigScreen {
        align: center middle;
    }
    #config_container {
        width: 70;
        height: auto;
        max-height: 80%;
        background: #1a1d23;
        border: thick $accent;
        padding: 1 2;
    }
    #config_title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    #config_content {
        padding: 1 0;
    }
    #close_config {
        dock: bottom;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="config_container"):
            yield Static("\u2699\ufe0f Configuration", id="config_title")
            with ScrollableContainer():
                content = CONFIG_FILE.read_text(encoding="utf-8") if CONFIG_FILE.exists() else "No config file found."
                yield Static(content, id="config_content", markup=False)
                yield Static("")
            yield Button("Close", variant="primary", id="close_config")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()


class ProviderSelectScreen(ModalScreen[str]):
    CSS = """
    ProviderSelectScreen {
        align: center middle;
    }
    #provider_container {
        width: 50;
        height: auto;
        max-height: 80%;
        background: #1a1d23;
        border: thick $accent;
        padding: 1 2;
    }
    #provider_title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    #close_provider {
        dock: bottom;
        margin-top: 1;
    }
    OptionList {
        background: transparent;
        border: none;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="provider_container"):
            yield Static("\U0001f50c Select Provider", id="provider_title")
            yield OptionList(id="provider_list")
            yield Button("Cancel", variant="primary", id="close_provider")

    def on_mount(self) -> None:
        settings = get_settings()
        option_list = self.query_one(OptionList)
        for p in settings.providers.keys():
            option_list.add_option(p)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.prompt))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class AddProviderScreen(ModalScreen[dict]):
    CSS = """
    AddProviderScreen {
        align: center middle;
    }
    #add_provider_container {
        width: 60;
        height: auto;
        background: #1a1d23;
        border: thick $accent;
        padding: 1 2;
    }
    #add_provider_title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    #add_provider_buttons {
        align: center middle;
        padding-top: 1;
        height: auto;
    }
    Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="add_provider_container"):
            yield Static("\u2795 Add Provider", id="add_provider_title")
            yield Input(placeholder="Provider Name (e.g. custom_openai)", id="input_name")
            yield Input(placeholder="Base URL (e.g. https://api.openai.com/v1)", id="input_url")
            yield Input(placeholder="API Key (optional)", id="input_key")
            with Horizontal(id="add_provider_buttons"):
                yield Button("Save", variant="success", id="btn_save")
                yield Button("Cancel", variant="error", id="btn_cancel")

    def on_mount(self) -> None:
        self.query_one("#input_name", Input).focus()

    def _save_provider(self) -> None:
        name = self.query_one("#input_name", Input).value.strip()
        url = self.query_one("#input_url", Input).value.strip()
        api_key = self.query_one("#input_key", Input).value.strip()
        
        if not name or not url:
            self.app.notify("Name and URL are required!", severity="error")
            return
            
        self.dismiss({"name": name, "url": url, "api_key": api_key})

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input_key":
            self._save_provider()
        else:
            self.focus_next()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            self._save_provider()
        else:
            self.dismiss(None)


class ApiKeyScreen(ModalScreen[str]):
    CSS = """
    ApiKeyScreen {
        align: center middle;
    }
    #api_key_container {
        width: 60;
        height: auto;
        background: #1a1d23;
        border: thick $accent;
        padding: 1 2;
    }
    #api_key_title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    #api_key_buttons {
        align: center middle;
        padding-top: 1;
        height: auto;
    }
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, provider_name: str, **kwargs):
        super().__init__(**kwargs)
        self._provider_name = provider_name

    def compose(self) -> ComposeResult:
        with Container(id="api_key_container"):
            yield Static(f"\U0001f5dd\ufe0f Set API Key for [{RUST}]{self._provider_name}[/{RUST}]", id="api_key_title")
            yield Input(placeholder="Enter API Key...", id="input_key")
            with Horizontal(id="api_key_buttons"):
                yield Button("Save", variant="success", id="btn_save")
                yield Button("Cancel", variant="error", id="btn_cancel")

    def on_mount(self) -> None:
        self.query_one("#input_key", Input).focus()

    def _save_key(self) -> None:
        key = self.query_one("#input_key", Input).value.strip()
        self.dismiss(key)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._save_key()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            self._save_key()
        else:
            self.dismiss(None)


class ModelsScreen(ModalScreen[str]):
    CSS = """
    ModelsScreen {
        align: center middle;
    }
    #models_container {
        width: 50;
        height: auto;
        max-height: 80%;
        background: #1a1d23;
        border: thick $accent;
        padding: 1 2;
    }
    #models_title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    #close_models {
        dock: bottom;
        margin-top: 1;
    }
    OptionList {
        background: transparent;
        border: none;
        height: 1fr;
        min-height: 5;
    }
    """

    def __init__(self, provider_name: str, **kwargs):
        super().__init__(**kwargs)
        self._provider_name = provider_name
        self._models: list[str] = []

    def compose(self) -> ComposeResult:
        with Container(id="models_container"):
            yield Static(f"\U0001f4cb Models [{RUST}]{self._provider_name}[/{RUST}]", id="models_title")
            yield Static("[dim]Fetching models...[/dim]", id="models_status")
            yield OptionList(id="models_list")
            yield Button("Cancel", variant="primary", id="close_models")

    async def on_mount(self) -> None:
        try:
            settings = get_settings()
            provider_obj = build_provider(self._provider_name, "", settings)
            self._models = await provider_obj.list_models()
            self.query_one("#models_status").remove()
            option_list = self.query_one(OptionList)
            for m in self._models:
                option_list.add_option(m)
        except Exception as e:
            self.query_one("#models_status").update(f"[red]Error: {e}[/red]")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.prompt))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class ConfirmScreen(ModalScreen[bool]):
    CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm_container {
        width: 55;
        height: auto;
        background: #1a1d23;
        border: thick #d1491f;
        padding: 1 2;
    }
    #confirm_title {
        text-style: bold;
        color: #d1491f;
        padding-bottom: 1;
    }
    #confirm_args {
        padding: 1 0;
        color: $text-muted;
    }
    #confirm_buttons {
        align: center middle;
        padding-top: 1;
    }
    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("shift+tab", "approve", "Auto-Approve"),
        ("escape", "reject", "Reject"),
    ]

    def __init__(self, tool_name: str, args: dict, **kwargs):
        super().__init__(**kwargs)
        self._tool_name = tool_name
        self._args = args

    def compose(self) -> ComposeResult:
        with Container(id="confirm_container"):
            yield Static("\u26a0\ufe0f  Action Request", id="confirm_title")
            yield Static(f"Tool: [bold]{self._tool_name}[/bold]")
            with ScrollableContainer():
                args_str = json.dumps(self._args, ensure_ascii=False, indent=2)
                yield Static(args_str, id="confirm_args", markup=False)
            with Horizontal(id="confirm_buttons"):
                yield Button("Yes", variant="error", id="confirm_yes")
                yield Button("No", variant="primary", id="confirm_no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm_yes")

    def action_approve(self) -> None:
        self.dismiss(True)

    def action_reject(self) -> None:
        self.dismiss(False)
