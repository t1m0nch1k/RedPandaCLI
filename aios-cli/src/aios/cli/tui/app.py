from __future__ import annotations

import os
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.events import Key
from textual.widgets import Footer, Header, Input, Static

from aios import __version__
from aios.cli.branding import CREAM, DIM, RUST, AgentState
from aios.cli.slash import dispatch_slash_with_action, get_available_commands
from aios.cli.tui.screens import (
    CommandPaletteScreen,
    ConfigScreen,
    ConfirmScreen,
    HelpScreen,
    HistoryScreen,
    ModelsScreen,
    ToolsScreen,
)
from aios.cli.tui.widgets import ChatMessage, CommandSuggestions, LogoWidget
from aios.config.settings import get_settings
from aios.core.models import Conversation, Role, StreamChunk
from aios.memory.history import history_store
from aios.providers.registry import build_provider
from aios.tools.registry import ToolRegistry


class AIOS_TUI(App):
    CSS = """
    Screen {
        background: #111318;
    }
    #main_container {
        layout: vertical;
        width: 100%;
        height: 100%;
    }
    #dashboard {
        height: auto;
        border-bottom: solid #d1491f;
        padding: 1 2;
        background: #181a20;
    }
    #dashboard_logo {
        width: auto;
        margin-right: 2;
    }
    #dashboard_info {
        width: 1fr;
        height: auto;
    }
    #dashboard_title {
        text-style: bold;
        color: $text;
    }
    #dashboard_version {
        color: $accent;
    }
    #dashboard_details {
        color: $text-muted;
    }
    #dashboard_mode {
        color: $accent;
    }
    #chat_area {
        height: 1fr;
        padding: 0 1;
        overflow-y: scroll;
        overflow-x: auto;
    }
    #input_container {
        height: auto;
        border-top: solid #d1491f;
        background: #181a20;
    }
    Input {
        border: none;
        background: #1a1d23;
        color: #f5ead8;
        margin: 0 1;
        padding: 1;
    }
    Input:focus {
        border: none;
    }
    #suggestions {
        width: 30;
        height: auto;
        max-height: 12;
        background: #1a1d23;
        border: solid #d1491f;
        margin: 0 1;
        display: none;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True, key_display="Ctrl+C"),
        Binding("ctrl+k", "show_commands", "Palette", key_display="Ctrl+K"),
        Binding("ctrl+t", "show_tools", "Tools", key_display="Ctrl+T"),
        Binding("ctrl+h", "show_history", "History", key_display="Ctrl+H"),
        Binding("ctrl+n", "new_conversation", "New", key_display="Ctrl+N"),
        Binding("ctrl+g", "show_config", "Config", key_display="Ctrl+G"),
        Binding("ctrl+y", "toggle_yolo", "YOLO", key_display="Ctrl+Y"),
        Binding("ctrl+s", "copy_last", "Copy AI", key_display="Ctrl+S"),
        Binding("escape", "cancel_gen", "Cancel", key_display="Esc"),
    ]

    def __init__(
        self,
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> None:
        super().__init__()
        self.settings = get_settings()
        self.provider_name = provider_name or self.settings.default_provider
        self.model_name = model_name or self.settings.default_model
        self.provider_obj = build_provider(self.provider_name, self.model_name, self.settings)
        self.tool_registry = ToolRegistry(git_config=self.settings.git)

        self.conversation = Conversation(provider=self.provider_name, model=self.model_name)
        self.agent_state: AgentState = AgentState.IDLE
        self.suggestion_index: int = 0
        self.mcp_servers: list[dict[str, Any]] = [s.model_dump() for s in self.settings.mcp_servers]
        self.git_config = self.settings.git
        self.yolo_mode: bool = False

    def compose(self) -> ComposeResult:
        workspace_name = os.path.basename(os.getcwd())

        yield Header()
        with Container(id="main_container"):
            with Horizontal(id="dashboard"):
                yield LogoWidget(AgentState.IDLE, id="dashboard_logo")
                with Vertical(id="dashboard_info"):
                    yield Static(
                        f"[bold {CREAM}]AIOS CLI[/bold {CREAM}]  [{RUST}]v{__version__}[/{RUST}]",
                        id="dashboard_title",
                    )
                    yield Static(
                        f"[{CREAM}]{self.provider_name}[/{CREAM}] \u00b7 "
                        f"[{CREAM}]{self.model_name}[/{CREAM}] \u00b7 "
                        f"[{DIM}]workspace: {workspace_name}[/{DIM}]",
                        id="dashboard_details",
                    )
                    yolo_tag = f" [{RUST}]YOLO[/{RUST}]" if getattr(self, "yolo_mode", False) else ""
                    yield Static(
                        f"[{RUST}]mode: auto[/{RUST}]{yolo_tag}",
                        id="dashboard_mode",
                    )
                    yield Static(
                        f"[{DIM}]msgs: 0 \u00b7 ~tokens: 0[/{DIM}]",
                        id="dashboard_stats",
                    )
            with ScrollableContainer(id="chat_area"):
                yield Static("[dim]Welcome to AIOS CLI. Ask me anything![/dim]")
            with Container(id="input_container"):
                yield CommandSuggestions(id="suggestions")
                yield Input(placeholder="Ask something...", id="input_area")
        yield Footer()

    # ── Input handling ──────────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        self._update_suggestions(event.value)

    def _update_suggestions(self, text: str) -> None:
        try:
            suggestions_widget = self.query_one("#suggestions", CommandSuggestions)
        except Exception:
            return

        prefix = "/provider "
        if text.startswith(prefix):
            providers = list(self.settings.providers.keys())
            filter_part = text[len(prefix):]
            filtered = [f"{prefix}{p}" for p in providers if p.startswith(filter_part)]
            if filtered:
                suggestions_widget.display = True
                self.suggestion_index = max(0, min(self.suggestion_index, len(filtered) - 1))
                suggestions_widget.update_suggestions(filtered, self.suggestion_index)
            else:
                suggestions_widget.display = False
        elif text.startswith("/"):
            all_cmds = get_available_commands()
            filtered = [cmd for cmd in all_cmds if cmd.startswith(text)]
            if filtered:
                suggestions_widget.display = True
                self.suggestion_index = max(0, min(self.suggestion_index, len(filtered) - 1))
                suggestions_widget.update_suggestions(filtered, self.suggestion_index)
            else:
                suggestions_widget.display = False
        else:
            suggestions_widget.display = False

    def action_show_commands(self) -> None:
        def on_cmd(cmd: str | None) -> None:
            if cmd:
                self.run_worker(self._handle_slash(cmd), exclusive=True)
        self.push_screen(CommandPaletteScreen(), on_cmd)

    def on_key(self, event: Key) -> None:
        try:
            suggestions_widget = self.query_one("#suggestions", CommandSuggestions)
        except Exception:
            return

        if not suggestions_widget.display or not suggestions_widget.suggestions:
            return

        if event.key == "up":
            event.stop()
            self.suggestion_index = (self.suggestion_index - 1) % len(suggestions_widget.suggestions)
            suggestions_widget.update_suggestions(
                suggestions_widget.suggestions, self.suggestion_index
            )
        elif event.key == "down":
            event.stop()
            self.suggestion_index = (self.suggestion_index + 1) % len(suggestions_widget.suggestions)
            suggestions_widget.update_suggestions(
                suggestions_widget.suggestions, self.suggestion_index
            )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            suggestions_widget = self.query_one("#suggestions", CommandSuggestions)
            input_widget = self.query_one("#input_area", Input)
        except Exception:
            return

        if suggestions_widget.display and suggestions_widget.suggestions:
            selected = suggestions_widget.suggestions[self.suggestion_index]
            input_widget.value = selected + " "
            input_widget.cursor_position = len(input_widget.value)
            suggestions_widget.display = False
            return

        text = event.value.strip()
        if not text:
            return

        input_widget.value = ""
        suggestions_widget.display = False

        self.run_worker(self._handle_input(text), exclusive=True)

    # ── Core message handling ───────────────────────────────────────

    async def _handle_input(self, text: str) -> None:
        if text.startswith("/"):
            await self._handle_slash(text)
            return

        self._add_message("user", text)
        self.conversation.add(Role.USER, text)
        history_store.ensure_conversation(self.conversation.id, self.provider_name, self.model_name)

        user_msg = self.conversation.messages[-1] if self.conversation.messages else None
        if user_msg:
            history_store.add_message(self.conversation.id, user_msg.id, "user", text)

        self._update_dashboard_stats()
        
        if hasattr(self, "_active_worker") and self._active_worker and not self._active_worker.is_finished:
            self._add_message("system", "Agent is already running. Press Esc to cancel.")
            return

        await self._run_agent()

    async def _handle_slash(self, text: str) -> None:
        cmd = text.strip().split(" ", 1)[0].lower()

        # TUI-native commands (use screens)
        TUI_CMDS = {
            "/exit": self._cmd_exit,
            "/quit": self._cmd_exit,
            "/clear": self._cmd_clear,
            "/help": self._cmd_help,
            "/tools": self._cmd_tools,
            "/history": self._cmd_history,
            "/config": self._cmd_config,
            "/models": self._cmd_models,
            "/model": self._cmd_model,
            "/provider": self._cmd_provider,
            "/add-provider": self._cmd_add_provider,
            "/key": self._cmd_key,
        }

        handler = TUI_CMDS.get(cmd)
        if handler is not None:
            await handler(text)
            return

        # Slash commands handled by TUI_CMDS will return early

        is_action, payload = await dispatch_slash_with_action(text)
        if is_action == "exit":
            self.exit()
        elif is_action == "clear":
            self._clear_chat()
        elif is_action == "message":
            self._add_message("system", str(payload))
        elif is_action:
            self._add_message("system", str(payload))
        else:
            self._add_message("system", f"Unknown command: [bold]{text}[/bold]")

    # ── Slash command handlers ──────────────────────────────────────

    async def _cmd_exit(self, text: str) -> None:
        self.exit()

    async def _cmd_clear(self, text: str) -> None:
        self._clear_chat()

    async def _cmd_help(self, text: str) -> None:
        self.push_screen(HelpScreen())

    async def _cmd_tools(self, text: str) -> None:
        self.push_screen(ToolsScreen(self.tool_registry))

    async def _cmd_history(self, text: str) -> None:
        self.push_screen(HistoryScreen())

    async def _cmd_config(self, text: str) -> None:
        self.push_screen(ConfigScreen())

    async def _cmd_models(self, text: str) -> None:
        self._open_model_select()

    async def _cmd_model(self, text: str) -> None:
        parts = text.strip().split(" ", 1)
        if len(parts) < 2:
            self._open_model_select()
            return
            
        new_model = parts[1].strip()
        self._switch_model(new_model)

    def _open_model_select(self) -> None:
        def on_model_selected(model: str | None) -> None:
            if model:
                self._switch_model(model)
        self.push_screen(ModelsScreen(self.provider_name), on_model_selected)

    def _switch_model(self, new_model: str) -> None:
        self.model_name = new_model
        
        from aios.config.settings import update_default_settings
        update_default_settings(model=new_model)
        
        self._rebuild_provider()
        self._refresh_dashboard()
        self._add_message("system", f"Model changed to: [bold]{new_model}[/bold]")
        self.notify(f"Model \u2192 {new_model}")

    async def _cmd_provider(self, text: str) -> None:
        parts = text.strip().split(" ", 1)
        if len(parts) < 2:
            def on_provider_selected(provider: str | None) -> None:
                if provider:
                    self._switch_provider(provider)
            from aios.cli.tui.screens import ProviderSelectScreen
            self.push_screen(ProviderSelectScreen(), on_provider_selected)
            return
            
        new_provider = parts[1].strip()
        self._switch_provider(new_provider)

    def _switch_provider(self, new_provider: str) -> None:
        if new_provider not in self.settings.providers:
            self._add_message(
                "system",
                f"Unknown provider: {new_provider}. Available: {', '.join(self.settings.providers)}",
            )
            return

        def _complete_switch() -> None:
            self.provider_name = new_provider
            
            from aios.config.settings import update_default_settings
            update_default_settings(provider=new_provider)
            
            self._rebuild_provider()
            self._refresh_dashboard()
            self._add_message("system", f"Provider changed to: [bold]{new_provider}[/bold]")
            self.notify(f"Provider \u2192 {new_provider}")
            self._open_model_select()

        provider_cfg = self.settings.providers[new_provider]
        api_key = (provider_cfg.api_key or "").strip()

        if not api_key and new_provider not in ["ollama", "lmstudio"]:
            def on_key_entered(key: str | None) -> None:
                if key:
                    from aios.config.settings import get_settings, set_api_key_in_config
                    set_api_key_in_config(new_provider, key)
                    self.settings = get_settings()
                    self._add_message("system", f"API Key updated for [bold]{new_provider}[/bold]")
                _complete_switch()
                
            from aios.cli.tui.screens import ApiKeyScreen
            self.push_screen(ApiKeyScreen(new_provider), on_key_entered)
        else:
            _complete_switch()

    async def _cmd_key(self, text: str) -> None:
        def on_key_entered(key: str | None) -> None:
            if key is not None:
                from aios.config.settings import get_settings, set_api_key_in_config
                set_api_key_in_config(self.provider_name, key)
                self.settings = get_settings()
                self._rebuild_provider()
                self._add_message("system", f"API Key updated for [bold]{self.provider_name}[/bold]")
                self.notify("API Key updated")

        from aios.cli.tui.screens import ApiKeyScreen
        self.push_screen(ApiKeyScreen(self.provider_name), on_key_entered)

    async def _cmd_add_provider(self, text: str) -> None:
        parts = text.strip().split(None, 3)
        if len(parts) < 3:
            def on_provider_added(result: dict[str, str] | None) -> None:
                if not result:
                    return
                name = result["name"]
                url = result["url"]
                api_key = result["api_key"]
                
                if name in self.settings.providers:
                    self._add_message("system", f"Provider [bold]{name}[/bold] already exists.")
                    return

                from aios.config.settings import add_provider_to_config, get_settings
                add_provider_to_config(name, url, api_key)
                self.settings = get_settings()
                self._refresh_dashboard()
                self._add_message("system", f"Provider [bold]{name}[/bold] added: {url}")
                self.notify(f"Provider +{name}")

            from aios.cli.tui.screens import AddProviderScreen
            self.push_screen(AddProviderScreen(), on_provider_added)
            return

        name = parts[1]
        endpoint = parts[2]
        api_key = parts[3] if len(parts) > 3 else ""

        if name in self.settings.providers:
            self._add_message("system", f"Provider [bold]{name}[/bold] already exists.")
            return

        from aios.config.settings import add_provider_to_config, get_settings
        add_provider_to_config(name, endpoint, api_key)
        self.settings = get_settings()
        self._refresh_dashboard()
        self._add_message(
            "system", f"Provider [bold]{name}[/bold] added: {endpoint}"
        )
        self.notify(f"Provider +{name}")

    # ── Agent loop ──────────────────────────────────────────────────

    async def _run_agent(self) -> None:
        self.agent_state = AgentState.THINKING
        self._update_logo()

        chat_area = self.query_one("#chat_area")
        chat_msg = ChatMessage("assistant", "")
        await chat_area.mount(chat_msg)
        chat_area.scroll_end(animate=False)

        try:
            user_msg_text = self.conversation.messages[-1].content if self.conversation.messages else ""
            intent = await self.runtime.classify_intent(user_msg_text)

            streamed_any = False
            async def on_stream(chunk: StreamChunk) -> None:
                nonlocal streamed_any
                if chunk.type == "content":
                    chat_msg.append_content(chunk.content)
                    chat_area.scroll_end(animate=False)
                    if chunk.content:
                        streamed_any = True

            from aios.runtime.models import IntentCategory
            if intent.category == IntentCategory.MISSION:
                self._add_message("system", "🚀 Autonomous mission started...")
                async for event in self.runtime.run_mission(user_msg_text, self.conversation):
                    content = getattr(event, "content", "") or getattr(event, "type", "")
                    if content:
                        chat_msg.append_content(f"[{event.type}] {content}\n")
                        chat_area.scroll_end(animate=False)
            else:
                reply = await self.runtime.chat(self.conversation, stream_callback=on_stream)
                
                if not streamed_any and reply:
                    chat_msg.append_content(reply)
                    chat_area.scroll_end(animate=False)

                assistant_msgs = [m for m in self.conversation.messages if m.role == Role.ASSISTANT]
                if assistant_msgs:
                    last = assistant_msgs[-1]
                    history_store.add_message(self.conversation.id, last.id, "assistant", reply)

            self._update_dashboard_stats()
            self.agent_state = AgentState.DONE
        except Exception as e:
            import logging
            logging.getLogger("aios").error(f"Error executing task: {e}", exc_info=True)
            try:
                await chat_msg.remove()
            except Exception:
                pass
            self._add_message("assistant", f"Error: {e}")
            self.agent_state = AgentState.ERROR

        self._update_logo()

    async def _confirm_action(self, tool_name: str, args: dict[str, Any]) -> bool:
        if getattr(self, "yolo_mode", False):
            return True
        screen = ConfirmScreen(tool_name, args)
        result = await self.push_screen_wait(screen)
        return result if result is not None else False

    def _on_agent_state(self, state: AgentState) -> None:
        self.agent_state = state
        self._update_logo()

    # ── Helpers ─────────────────────────────────────────────────────

    def _rebuild_provider(self) -> None:
        try:
            self.provider_obj = build_provider(self.provider_name, self.model_name, self.settings)
            
            # Rebuild runtime if it exists
            if hasattr(self, "runtime"):
                self.runtime._config.provider = self.provider_obj
        except ValueError as e:
            self._add_message("system", f"Error switching: {e}")

    def _refresh_dashboard(self) -> None:
        try:
            workspace = os.path.basename(os.getcwd())
            self.query_one("#dashboard_details", Static).update(
                f"[{CREAM}]{self.provider_name}[/{CREAM}] \u00b7 "
                f"[{CREAM}]{self.model_name}[/{CREAM}] \u00b7 "
                f"[{DIM}]workspace: {workspace}[/{DIM}]"
            )
        except Exception:
            pass

    def _update_logo(self) -> None:
        try:
            self.query_one("#dashboard_logo", LogoWidget).set_state(self.agent_state)
        except Exception:
            pass

    def _clear_chat(self) -> None:
        chat_area = self.query_one("#chat_area")
        chat_area.remove_children()
        self.conversation = Conversation(provider=self.provider_name, model=self.model_name)
        self.agent_state = AgentState.IDLE
        self._update_logo()
        self._update_dashboard_stats()
        self._add_message("system", "Conversation cleared. Start fresh!")

    def _add_message(self, role: str, content: str) -> None:
        try:
            chat_area = self.query_one("#chat_area")
            msg = ChatMessage(role, content)
            chat_area.mount(msg)
            chat_area.scroll_end(animate=False)
        except Exception:
            pass

    # ── App actions (keyboard shortcuts) ────────────────────────────

    def action_show_commands(self) -> None:
        self.push_screen(HelpScreen())

    def action_show_tools(self) -> None:
        self.push_screen(ToolsScreen(self.tool_registry))

    def action_show_history(self) -> None:
        self.push_screen(HistoryScreen())

    def action_show_config(self) -> None:
        self.push_screen(ConfigScreen())

    def action_new_conversation(self) -> None:
        self._clear_chat()
        self.notify("New conversation started")

    def action_toggle_yolo(self) -> None:
        self.yolo_mode = not getattr(self, "yolo_mode", False)
        status = "ENABLED" if self.yolo_mode else "DISABLED"
        self._add_message("system", f"YOLO mode [bold]{status}[/bold]. (Auto-approve actions)")
        self._update_dashboard_mode()
        self.notify(f"YOLO Mode: {status}")


    def action_copy_last(self) -> None:
        ai_msgs = [m for m in self.conversation.messages if m.role.value == "assistant"]
        if ai_msgs:
            try:
                self.copy_to_clipboard(ai_msgs[-1].content)
                self.notify("Copied last AI message!")
            except Exception as e:
                self.notify(f"Copy failed: {e}", severity="error")
        else:
            self.notify("No AI messages to copy.", severity="warning")

    def action_cancel_gen(self) -> None:
        worker = getattr(self, "_active_worker", None)
        if worker and not worker.is_finished:
            worker.cancel()
            self._add_message("system", "[bold red]Generation cancelled.[/bold red]")
            self.agent_state = AgentState.IDLE
            self._update_logo()
            self.notify("Cancelled", severity="warning")

    def _update_dashboard_mode(self) -> None:
        try:
            yolo_tag = f" [{RUST}]YOLO[/{RUST}]" if getattr(self, "yolo_mode", False) else ""
            self.query_one("#dashboard_mode", Static).update(
                f"[{RUST}]mode: auto[/{RUST}]{yolo_tag}"
            )
        except Exception:
            pass

    def _update_dashboard_stats(self) -> None:
        try:
            msgs_count = len(self.conversation.messages)
            chars = sum(len(m.content) for m in self.conversation.messages)
            # Rough approximation: 1 token ≈ 4 characters
            tokens = chars // 4
            self.query_one("#dashboard_stats", Static).update(
                f"[{DIM}]msgs: {msgs_count} \u00b7 ~tokens: {tokens}[/{DIM}]"
            )
        except Exception:
            pass

    # ── Lifecycle ───────────────────────────────────────────────────

    async def on_mount(self) -> None:
        self.title = "AIOS CLI"
        self.sub_title = f"v{__version__}"

        from aios.executor.coding_agent import CODING_SYSTEM_PROMPT
        from aios.runtime.runtime import Runtime, RuntimeConfig
        config = RuntimeConfig(
            provider=self.provider_obj,
            tool_registry=self.tool_registry,
            mcp_enabled=bool(self.mcp_servers),
            state_callback=self._on_agent_state,
            confirmation_callback=self._confirm_action,
            system_prompt=CODING_SYSTEM_PROMPT,
        )
        self.runtime = Runtime(config)
        await self.runtime.__aenter__()

    async def on_unmount(self) -> None:
        if hasattr(self, "runtime"):
            await self.runtime.__aexit__(None, None, None)

