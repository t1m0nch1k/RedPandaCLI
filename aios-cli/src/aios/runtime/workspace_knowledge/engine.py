from __future__ import annotations

import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkspaceKnowledgeEngine:
    """
    Scans the workspace to build a lightweight, queryable index of symbols
    (classes, functions, methods) to help the agent find code faster.
    """
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self._index: dict[str, list[dict]] = {}
        self._initialized = False

    def build_index(self) -> None:
        """
        Walks the workspace and builds an index of Python files and their AST symbols.
        """
        if self._initialized:
            return
            
        self._index = {}
        count = 0
        
        try:
            for path in self.workspace_root.rglob("*.py"):
                # Skip virtual environments and hidden directories
                if any(part.startswith(".") for part in path.parts) or "venv" in path.parts or "node_modules" in path.parts:
                    continue
                    
                rel_path = str(path.relative_to(self.workspace_root))
                symbols = self._parse_file(path)
                
                for sym in symbols:
                    name = sym["name"]
                    if name not in self._index:
                        self._index[name] = []
                    self._index[name].append({
                        "file": rel_path,
                        "type": sym["type"],
                        "line": sym["line"],
                        "doc": sym["doc"]
                    })
                count += 1
        except Exception as e:
            logger.error(f"Failed to build workspace index: {e}")
            
        self._initialized = True
        logger.info(f"Workspace index built: {len(self._index)} symbols across {count} files.")

    def _parse_file(self, file_path: Path) -> list[dict]:
        symbols = []
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    doc = ast.get_docstring(node)
                    symbols.append({
                        "name": node.name,
                        "type": "class",
                        "line": node.lineno,
                        "doc": doc[:100] + "..." if doc and len(doc) > 100 else doc
                    })
                    # Add methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            mdoc = ast.get_docstring(item)
                            symbols.append({
                                "name": item.name,
                                "type": "method",
                                "line": item.lineno,
                                "doc": mdoc[:100] + "..." if mdoc and len(mdoc) > 100 else mdoc
                            })
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    doc = ast.get_docstring(node)
                    symbols.append({
                        "name": node.name,
                        "type": "function",
                        "line": node.lineno,
                        "doc": doc[:100] + "..." if doc and len(doc) > 100 else doc
                    })
        except Exception:
            # Silently ignore syntax errors or unreadable files during indexing
            pass
            
        return symbols

    def search(self, query: str) -> str:
        """
        Searches the index for a given symbol name (exact or substring match).
        """
        if not self._initialized:
            self.build_index()
            
        results = []
        for sym_name, locations in self._index.items():
            if query.lower() in sym_name.lower():
                for loc in locations:
                    results.append(
                        f"- `{sym_name}` ({loc['type']}) in {loc['file']}:{loc['line']}"
                        + (f"\n  Doc: {loc['doc']}" if loc['doc'] else "")
                    )
                    
        if not results:
            return f"No symbols matching '{query}' found in the indexed Python files."
            
        header = f"Found {len(results)} matches for '{query}':\n"
        return header + "\n".join(results[:20]) # Limit output size
