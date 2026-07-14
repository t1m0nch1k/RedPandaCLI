from __future__ import annotations

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

from aios.cli.branding import LOGOS, PIXEL_COLORS, RUST, AgentState


class LogoWidget(Static):
    def __init__(self, state: AgentState = AgentState.IDLE, **kwargs):
        self._state = state
        super().__init__("", **kwargs)

    def on_mount(self) -> None:
        self._render_pixels()

    def set_state(self, state: AgentState) -> None:
        if state != self._state:
            self._state = state
            self._render_pixels()

    def _render_pixels(self) -> None:
        logo_data = LOGOS.get(self._state, LOGOS[AgentState.IDLE])
        icon = Text()
        for line in logo_data:
            for pixel in line:
                color = PIXEL_COLORS.get(pixel)
                icon.append("██" if color else "  ", style=color or "")
            icon.append("\n")
        self.update(icon)


class ChatMessage(Static):
    def __init__(self, role: str, content: str, **kwargs):
        self._role = role
        self._content = content
        super().__init__("", **kwargs)

    def on_mount(self) -> None:
        self._render_panel()

    def append_content(self, delta: str) -> None:
        self._content += delta
        self._render_panel()

    def _render_panel(self) -> None:
        if self._role == "user":
            style = "white"
            title = "You"
            border_style = "#4a9eff"
        elif self._role == "assistant":
            style = "cyan"
            title = "AIOS"
            border_style = "#00d4aa"
        elif self._role == "system":
            style = "yellow"
            title = "System"
            border_style = "#d1491f"
        else:
            style = "dim"
            title = self._role
            border_style = "grey58"

        if self._role == "user" or self._role == "system":
            text = Text(self._content, style=style)
            panel = Panel(text, title=title, border_style=border_style)
        else:
            display_content = self._content
            if not display_content:
                display_content = "> **💭 Thinking...**\n\n"
            else:
                if "<think>" in display_content and "</think>" not in display_content:
                    display_content += "\n</think>"
                if "<thought>" in display_content and "</thought>" not in display_content:
                    display_content += "\n</thought>"

            import re
            def think_replacer(match):
                think_content = match.group(1).strip()
                if not think_content:
                    return "> **💭 Thinking...**\n\n"
                lines = think_content.split('\n')
                quoted = '\n'.join([f"> {line}" for line in lines])
                return f"> **💭 Thoughts:**\n{quoted}\n\n"

            display_content = re.sub(r'<think>(.*?)</think>', think_replacer, display_content, flags=re.DOTALL)
            display_content = re.sub(r'<thought>(.*?)</thought>', think_replacer, display_content, flags=re.DOTALL)

            md = Markdown(display_content)
            panel = Panel(md, title=title, border_style=border_style)
            
        self.update(panel)


class CommandSuggestions(Static):
    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self.suggestions: list[str] = []
        self.selected_index: int = 0

    def update_suggestions(self, suggestions: list[str], selected_index: int = 0) -> None:
        self.suggestions = suggestions
        self.selected_index = selected_index
        self._render_list()

    def _render_list(self) -> None:
        if not self.suggestions:
            self.update("")
            return
            
        MAX_VISIBLE = 10
        # Calculate window to keep selected_index visible
        start_idx = max(0, min(self.selected_index - MAX_VISIBLE // 2, len(self.suggestions) - MAX_VISIBLE))
        end_idx = start_idx + MAX_VISIBLE
        
        visible_suggestions = self.suggestions[start_idx:end_idx]
        
        text = Text()
        if start_idx > 0:
            text.append("   \u2191 ...\n", style="dim")
            
        for i, cmd in enumerate(visible_suggestions):
            actual_idx = start_idx + i
            style = f"bold {RUST}" if actual_idx == self.selected_index else "#f5ead8"
            prefix = " \u25b8 " if actual_idx == self.selected_index else "   "
            text.append(f"{prefix}{cmd}\n", style=style)
            
        if end_idx < len(self.suggestions):
            text.append(f"   \u2193 ... ({self.selected_index + 1}/{len(self.suggestions)})\n", style="dim")
            
        self.update(text)
