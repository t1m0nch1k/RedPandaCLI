from __future__ import annotations

from pathlib import Path

from aios.memory.auto import AutoMemory
from aios.memory.long_term import LongTermMemory
from aios.memory.project import ProjectMemory


class MemoryOrchestrator:
    """
    Coordinates access to various memory systems:
    - ProjectMemory (AIOS.md context)
    - AutoMemory (learned facts about the workspace)
    - (Future) UserMemory, etc.
    """
    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root
        self.project_memory = ProjectMemory(workspace_root) if workspace_root else None
        self.auto_memory = AutoMemory(workspace_root) if workspace_root else None
        
        db_path = Path.home() / ".aios" / "long_term.db"
        self.long_term = LongTermMemory(db_path)

    def get_active_context(self) -> str:
        """
        Retrieves all relevant memory contexts combined into a single string
        to be injected into the system prompt.
        """
        parts = []
        
        # 1. Load explicit instructions (AIOS.md hierarchy)
        if self.project_memory:
            proj_context = self.project_memory.load_context()
            if proj_context:
                parts.append(proj_context)
                
        # 2. Load automatic memory (learned facts)
        if self.auto_memory:
            auto_context = self.auto_memory.recall(limit=20)
            if auto_context:
                parts.append(auto_context)
                
        return "\n\n".join(parts) if parts else ""

    def add_fact(self, fact: str, source: str = "agent") -> None:
        """
        Learns a new fact about the workspace.
        """
        if self.auto_memory:
            self.auto_memory.add_fact(fact, source)
        
        # Also mirror to LongTermMemory for better searchability
        self.long_term.store(
            content=fact,
            category="fact",
            tags=[source]
        )
