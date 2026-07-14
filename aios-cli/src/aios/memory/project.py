from __future__ import annotations

from pathlib import Path

from aios.config.settings import CONFIG_DIR


class ProjectMemory:
    """
    Handles loading of hierarchical AIOS.md files from the workspace.
    """
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.global_memory_path = CONFIG_DIR / "AIOS.md"

    def _find_aios_files(self) -> list[Path]:
        """
        Finds all AIOS.md files in the project hierarchy safely.
        """
        import os
        
        files = []
        root_aios = self.workspace_root / "AIOS.md"
        if root_aios.exists():
            files.append(root_aios)
        
        exclude_dirs = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".aios", "dist", "build"}
        
        try:
            for root, dirs, filenames in os.walk(self.workspace_root):
                # Modify dirs in-place to prune the search tree
                dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
                
                # Limit depth to 5
                try:
                    rel_path = Path(root).relative_to(self.workspace_root)
                    if len(rel_path.parts) > 5:
                        dirs[:] = []
                        continue
                except ValueError:
                    continue
                    
                if "AIOS.md" in filenames:
                    path = Path(root) / "AIOS.md"
                    if path != root_aios:
                        files.append(path)
        except Exception:
            pass
                
        return files

    def load_context(self) -> str:
        """
        Aggregates content from all found AIOS.md files into a single system prompt.
        """
        contexts = []
        
        # 1. Global AIOS.md from ~/.aios/
        if self.global_memory_path.exists():
            with open(self.global_memory_path, encoding="utf-8") as f:
                content = f.read()
                contexts.append(f"### GLOBAL INSTRUCTIONS\n{content}")

        # 2. Project-level and directory-level AIOS.md files
        aios_files = self._find_aios_files()
        for path in aios_files:
            relative_path = path.relative_to(self.workspace_root)
            with open(path, encoding="utf-8") as f:
                content = f.read()
                contexts.append(f"### CONTEXT: {relative_path}\n{content}")

        if not contexts:
            return ""

        return "\n\n".join(contexts)
