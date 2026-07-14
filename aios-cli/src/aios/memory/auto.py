from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aios.config.settings import CONFIG_DIR


class AutoMemory:
    """
    Handles the agent's automatic memory of facts about the workspace.
    Stored in ~/.aios/memory/<workspace_hash>.jsonl
    """
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.memory_dir = CONFIG_DIR / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a hash of the workspace path to create a unique file for each project
        self.workspace_hash = hashlib.sha256(str(workspace_root).encode()).hexdigest()[:16]
        self.memory_file = self.memory_dir / f"{self.workspace_hash}.jsonl"

    def add_fact(self, fact: str, source: str = "agent") -> None:
        """Adds a new fact to the project's automatic memory."""
        entry = {
            "fact": fact,
            "source": source,
            "timestamp": str(Path().absolute()) # Simplified timestamp for now
        }
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def recall(self, limit: int = 10) -> str:
        """Recalls the last N facts as a summarized string."""
        if not self.memory_file.exists():
            return ""
            
        facts = []
        try:
            with open(self.memory_file, encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if len(facts) >= limit:
                        break
                    entry = json.loads(line)
                    facts.append(f"- {entry['fact']} (source: {entry['source']})")
        except Exception:
            return ""
            
        if not facts:
            return ""
            
        return "### AUTOMATIC MEMORY\n" + "\n".join(facts)
