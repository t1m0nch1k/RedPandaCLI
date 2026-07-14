from __future__ import annotations

import uuid
from datetime import datetime

from rich.console import Group
from rich.table import Table
from rich.text import Text

from aios.runtime.models import ExecutionState

RUST = "#d1491f"
CREAM = "#f5ead8"
DIM = "grey58"

# AgentState is the canonical import for CLI/TUI code.
# Defined in runtime/models as ExecutionState to avoid confusion
# with the Runtime's 11-state AgentState.
AgentState = ExecutionState

# Base logo structure
# R = Red, D = Dark Red, W = White, K = Black
# Eyes are around line 6-8, Mouth around line 10
LOGOS = {
    AgentState.IDLE: [
        "WWK   RR  KWW",
        "WKWRRRRRRRWKW",
        "WKRRRRRRRRRKW",
        "WRRRRRRRRRRRW",
        " RRRRRRRRRRR ",
        "RRRRWRRRWRRRR",
        "RWWRKRRRKRWWR",
        "WWDDKRWRKDDWW",
        "WDDDWWKWWDDDW",
        " WDDWWKWWDDW ",
        "   DWWWWWD   ",
    ],
    AgentState.THINKING: [
        "WWK   RR  KWW",
        "WKWRRRRRRRWKW",
        "WKRRRRRRRRRKW",
        "WRRRRRRRRRRRW",
        " RRRRRRRRRRR ",
        "RRRRKRRRKRRRR", # Eyes: K (closed/flat)
        "RWWRKRRRKRWWR",
        "WWDDKRWRKDDWW",
        "WDDDWWKWWDDDW",
        " WDDWWKWWDDW ",
        "   DWWWWWD   ",
    ],
    AgentState.TOOL: [
        "WWK   RR  KWW",
        "WKWRRRRRRRWKW",
        "WKRRRRRRRRRKW",
        "WRRRRRRRRRRRW",
        " RRRRRRRRRRR ",
        "RRRR•RRR•RRRR", # Eyes: • (focused)
        "RWWRKRRRKRWWR",
        "WWDDKRWRKDDWW",
        "WDDDWWKWWDDDW",
        " WDDWWKWWDDW ",
        "   DWWWWWD   ",
    ],
    AgentState.ERROR: [
        "WWK   RR  KWW",
        "WKWRRRRRRRWKW",
        "WKRRRRRRRRRKW",
        "WRRRRRRRRRRRW",
        " RRRRRRRRRRR ",
        "RRRR>RRR<RRRR", # Eyes: > < (distressed)
        "RWWRKRRRKRWWR",
        "WWDDKRWRKDDWW",
        "WDDDWWKWWDDDW",
        " WDDDWKDWDDW ", # Mouth: frowning
        "   DWWWWWD   ",
    ],
    AgentState.DONE: [
        "WWK   RR  KWW",
        "WKWRRRRRRRWKW",
        "WKRRRRRRRRRKW",
        "WRRRRRRRRRRRW",
        " RRRRRRRRRRR ",
        "RRRR^RRR^RRRR", # Eyes: ^ (happy)
        "RWWRKRRRKRWWR",
        "WWDDKRWRKDDWW",
        "WDDDWWKWWDDDW",
        " WDDWWKWWDDW ",
        "   DWWWWWD   ",
    ],
}

PIXEL_COLORS = {
    "R": "#c83a18",
    "D": "#8e270f",
    "W": "#f7f3ef",
    "K": "#111318",
    "•": "#ffffff",
    ">": "#ffffff",
    "<": "#ffffff",
    "^": "#ffffff",
    "-": "#ffffff",
}


def _render_pixel_logo(state: AgentState) -> Text:
    logo_data = LOGOS.get(state, LOGOS[AgentState.IDLE])
    icon = Text()
    for line in logo_data:
        for pixel in line:
            color = PIXEL_COLORS.get(pixel)
            icon.append("██" if color else "  ", style=color or "")
        icon.append("\n")
    return icon


def render_session_id() -> str:
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


def render_dashboard(
    version: str,
    provider: str,
    model: str,
    tools: list[str],
    providers: list[str],
    session_id: str,
    state: AgentState = AgentState.IDLE,
) -> Group:
    header = Table.grid(padding=(0, 3))
    header.add_column()
    header.add_column()

    info = Text()
    info.append("AIOS CLI ", style=f"bold {CREAM}")
    info.append(f"v{version}\n", style=f"bold {RUST}")
    info.append(f"{provider}", style=f"bold {CREAM}")
    info.append(" · ", style=DIM)
    info.append(f"{model}\n\n", style=f"bold {CREAM}")

    info.append("Available Tools\n", style=f"bold {RUST}")
    info.append("  " + ", ".join(tools) + "\n\n", style=DIM)

    info.append("Available Providers\n", style=f"bold {RUST}")
    info.append("  " + ", ".join(providers), style=DIM)

    header.add_row(_render_pixel_logo(state), info)

    status = Text()
    status.append(f"{len(tools)} tools", style=DIM)
    status.append("  ·  ", style=DIM)
    status.append(f"{len(providers)} providers", style=DIM)
    status.append("  ·  ", style=DIM)
    status.append(f"session {session_id}", style=DIM)

    return Group(header, Text(""), status)


def render_mini_prompt_label(label: str) -> Text:
    return Text.assemble(("\U0001F43E ", "bold"), (label, f"bold {RUST}"))
