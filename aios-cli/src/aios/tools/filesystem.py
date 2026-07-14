from __future__ import annotations

import difflib
import fnmatch
import re
import shutil
from pathlib import Path
from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool
from aios.workspace import WorkspaceContext


class FilesystemTool(Tool):
    name = "filesystem"
    description = "Advanced file system operations: read, write, search, surgical edit, multi-file batch, and diff"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list_files", "read_file", "read_file_range",
                    "create_file", "create_folder", "delete",
                    "replace_text", "search_text", "get_project_structure",
                    "multi_edit", "rename_symbol", "move_file",
                    "preview_diff", "apply_patch",
                ],
                "description": "The filesystem action to perform",
            },
            "path": {"type": "string", "description": "Path to the file or directory"},
            "content": {"type": "string", "description": "Content to write to a file"},
            "start_line": {"type": "integer", "description": "Start line for range reading (1-indexed)"},
            "end_line": {"type": "integer", "description": "End line for range reading (1-indexed)"},
            "old_text": {"type": "string", "description": "Exact text to be replaced"},
            "new_text": {"type": "string", "description": "Text to replace with"},
            "recursive": {"type": "boolean", "description": "Whether to list files recursively"},
            "pattern": {"type": "string", "description": "Text or regex pattern to search for"},
            "max_depth": {"type": "integer", "description": "Maximum depth for project structure (default: 3)"},
            "operations": {
                "type": "array",
                "description": "Array of {path, old_text, new_text} for multi_edit",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                    },
                    "required": ["path", "old_text", "new_text"],
                },
            },
            "old_name": {"type": "string", "description": "Symbol name to rename (for rename_symbol)"},
            "new_name": {"type": "string", "description": "New symbol name (for rename_symbol)"},
            "file_pattern": {"type": "string", "description": "Glob pattern for files to include (e.g. '**/*.py')"},
            "source": {"type": "string", "description": "Source path (for move_file)"},
            "destination": {"type": "string", "description": "Destination path (for move_file)"},
            "patch_text": {"type": "string", "description": "Unified diff text to apply (for apply_patch)"},
            "context_lines": {"type": "integer", "description": "Number of context lines for diff preview (default: 3)"},
        },
        "required": ["action"],
    }

    def __init__(self, workspace: WorkspaceContext | None = None) -> None:
        self.workspace = workspace or WorkspaceContext.from_cwd()

    def _get_ignore_patterns(self) -> list[str]:
        ignore_file = self.workspace.root / ".aiosignore"
        if ignore_file.exists():
            return [
                line.strip()
                for line in ignore_file.read_text().splitlines()
                if line.strip() and not line.startswith("#")
            ]
        return [".git", "__pycache__", ".venv", "node_modules", ".idea", ".vscode"]

    def _is_ignored(self, path: Path, root: Path, patterns: list[str]) -> bool:
        rel_path = str(path.relative_to(root))
        for pattern in patterns:
            if fnmatch.fnmatch(rel_path, pattern) or any(
                fnmatch.fnmatch(part, pattern) for part in path.relative_to(root).parts
            ):
                return True
        return False

    async def run(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        root = self.workspace.root
        req_path = kwargs.get("path")
        if req_path is None:
            req_path = "."
            
        try:
            path = self.workspace.require_path(req_path)
        except ValueError as exc:
            return ToolResult(success=False, error=str(exc))
        patterns = self._get_ignore_patterns()

        if action == "list_files":
            if not path.exists():
                return ToolResult(success=False, error=f"{path} does not exist")
            
            recursive = kwargs.get("recursive", False)
            pattern = "**/*" if recursive else "*"
            files = []
            for p in path.glob(pattern):
                if not self._is_ignored(p, root, patterns):
                    files.append(self.workspace.display_path(p))
            return ToolResult(success=True, output="\n".join(files) or "No files found")

        if action == "get_project_structure":
            if not path.exists():
                return ToolResult(success=False, error=f"{path} does not exist")
            
            max_depth = kwargs.get("max_depth", 3)
            tree = []

            def build_tree(current_path: Path, depth: int):
                if depth > max_depth:
                    return
                
                try:
                    entries = sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                    for entry in entries:
                        if self._is_ignored(entry, root, patterns):
                            continue
                        
                        indent = "  " * depth
                        suffix = "/" if entry.is_dir() else ""
                        tree.append(f"{indent}├── {entry.name}{suffix}")
                        
                        if entry.is_dir():
                            build_tree(entry, depth + 1)
                except PermissionError:
                    tree.append(f"  {'  ' * depth}└── [Permission Denied]")

            build_tree(path, 0)
            return ToolResult(success=True, output="\n".join(tree) or "Empty directory")

        if action == "read_file":
            if not path.exists():
                return ToolResult(success=False, error=f"{path} does not exist")
            return ToolResult(success=True, output=path.read_text(encoding="utf-8"))

        if action == "read_file_range":
            if not path.exists():
                return ToolResult(success=False, error=f"{path} does not exist")
            
            start = kwargs.get("start_line", 1)
            end = kwargs.get("end_line")
            
            lines = path.read_text(encoding="utf-8").splitlines()
            selected = lines[max(0, start-1) : (end if end else len(lines))]
            return ToolResult(success=True, output="\n".join(selected))

        if action == "create_file":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(kwargs.get("content", ""), encoding="utf-8")
            return ToolResult(success=True, output=f"Created file {path}")

        if action == "create_folder":
            path.mkdir(parents=True, exist_ok=True)
            return ToolResult(success=True, output=f"Created folder {path}")

        if action == "delete":
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()
            return ToolResult(success=True, output=f"Deleted {path}")

        if action == "replace_text":
            if not path.exists():
                return ToolResult(success=False, error=f"{path} does not exist")
            
            old_text = kwargs.get("old_text")
            new_text = kwargs.get("new_text")
            if old_text is None or new_text is None:
                return ToolResult(success=False, error="Both old_text and new_text are required")
            
            content = path.read_text(encoding="utf-8")
            if old_text not in content:
                return ToolResult(success=False, error=f"Could not find exact match for old_text in {path}")
            
            matches = content.count(old_text)
            if matches > 1:
                return ToolResult(
                    success=False,
                    error=f"Found {matches} matches for old_text in {path}; make it more specific",
                )

            new_content = content.replace(old_text, new_text, 1)
            path.write_text(new_content, encoding="utf-8")
            return ToolResult(success=True, output=f"Successfully replaced text in {path}")

        if action == "search_text":
            if not path.exists():
                return ToolResult(success=False, error=f"{path} does not exist")
            
            pattern = kwargs.get("pattern", "")
            results = []
            
            if path.is_file():
                files = [path]
            else:
                files = path.rglob("*")
            
            for f in files:
                if f.is_file() and not self._is_ignored(f, root, patterns):
                    try:
                        content = f.read_text(encoding="utf-8")
                        for i, line in enumerate(content.splitlines(), 1):
                            if re.search(pattern, line):
                                results.append(f"{f.relative_to(root)}:{i}: {line.strip()}")
                    except Exception:
                        continue
            
            return ToolResult(success=True, output="\n".join(results) or "No matches found")

        if action == "multi_edit":
            operations = kwargs.get("operations", [])
            if not operations:
                return ToolResult(success=False, error="No operations provided. Use 'operations' array.")
            if not isinstance(operations, list):
                return ToolResult(success=False, error="'operations' must be an array.")

            backup: dict[str, str] = {}
            resolved: dict[str, Path] = {}
            try:
                for op in operations:
                    p = self.workspace.require_path(op.get("path", ""))
                    if not p.exists():
                        raise FileNotFoundError(f"{p} does not exist")
                    p_str = str(p)
                    resolved[p_str] = p
                    backup[p_str] = p.read_text(encoding="utf-8")

                for op in operations:
                    p = self.workspace.require_path(op["path"])
                    p_str = str(p)
                    content = p.read_text(encoding="utf-8")
                    old = op["old_text"]
                    new = op["new_text"]
                    if old not in content:
                        raise ValueError(f"Could not find old_text in {p}")
                    if content.count(old) > 1:
                        raise ValueError(f"Found {content.count(old)} matches for old_text in {p}; make it more specific")
                    p.write_text(content.replace(old, new, 1), encoding="utf-8")

                return ToolResult(
                    success=True,
                    output=f"Successfully applied {len(operations)} edit(s) across {len(resolved)} file(s)",
                )
            except (FileNotFoundError, ValueError, OSError) as e:
                for path_str, original in backup.items():
                    Path(path_str).write_text(original, encoding="utf-8")
                return ToolResult(success=False, error=f"multi_edit failed, all changes rolled back: {e}")

        if action == "rename_symbol":
            old_name = kwargs.get("old_name", "")
            new_name = kwargs.get("new_name", "")
            if not old_name or not new_name:
                return ToolResult(success=False, error="Both 'old_name' and 'new_name' are required")
            search_root = path if path.exists() else root
            file_pattern = kwargs.get("file_pattern", "**/*")
            if search_root.is_file():
                files = [search_root]
            else:
                files = [f for f in search_root.glob(file_pattern) if f.is_file() and not self._is_ignored(f, root, patterns)]

            backup: dict[str, str] = {}
            changed = []
            try:
                for f in files:
                    try:
                        content = f.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    if old_name not in content:
                        continue
                    backup[str(f)] = content
                    new_content = content.replace(old_name, new_name)
                    f.write_text(new_content, encoding="utf-8")
                    changed.append(str(f))

                if not changed:
                    return ToolResult(success=True, output=f"No files contained '{old_name}'")
                return ToolResult(
                    success=True,
                    output=f"Renamed '{old_name}' → '{new_name}' in {len(changed)} file(s):\n" + "\n".join(changed),
                )
            except OSError as e:
                for path_str, original in backup.items():
                    Path(path_str).write_text(original, encoding="utf-8")
                return ToolResult(success=False, error=f"rename_symbol failed, rolled back: {e}")

        if action == "move_file":
            source_str = kwargs.get("source", "")
            dest_str = kwargs.get("destination", "")
            if not source_str or not dest_str:
                return ToolResult(success=False, error="Both 'source' and 'destination' are required")
            try:
                src = self.workspace.require_path(source_str)
                dst = self.workspace.require_path(dest_str)
            except ValueError as e:
                return ToolResult(success=False, error=str(e))

            if not src.exists():
                return ToolResult(success=False, error=f"Source does not exist: {src}")
            if dst.exists():
                return ToolResult(success=False, error=f"Destination already exists: {dst}")

            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)

            rel_src = self.workspace.display_path(src)
            rel_dst = self.workspace.display_path(dst)

            if src.suffix == ".py":
                import_updates = 0
                py_files = list(root.rglob("*.py")) if root != dst else []
                for pf in py_files:
                    if pf == dst or self._is_ignored(pf, root, patterns):
                        continue
                    try:
                        content = pf.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    old_import = src.stem
                    new_import = dst.stem
                    if old_import in content and old_import != new_import:
                        updated = content.replace(old_import, new_import)
                        pf.write_text(updated, encoding="utf-8")
                        import_updates += 1

                msg = f"Moved {rel_src} → {rel_dst}"
                if import_updates:
                    msg += f" and updated imports in {import_updates} file(s)"
                return ToolResult(success=True, output=msg)

            return ToolResult(success=True, output=f"Moved {rel_src} → {rel_dst}")

        if action == "preview_diff":
            old_text = kwargs.get("old_text", "")
            new_text = kwargs.get("new_text", "")
            if not old_text and not new_text:
                return ToolResult(success=False, error="'old_text' or 'new_text' required")
            display_path = self.workspace.display_path(path) if 'path' in kwargs else "file"
            context = kwargs.get("context_lines", 3)

            old_lines = old_text.splitlines(keepends=True)
            new_lines = new_text.splitlines(keepends=True)
            diff = list(difflib.unified_diff(
                old_lines, new_lines,
                fromfile=display_path, tofile=display_path,
                n=context,
            ))
            diff_text = "".join(diff)
            if not diff_text.strip():
                return ToolResult(success=True, output="No differences found")
            return ToolResult(success=True, output=diff_text, data={"diff": diff_text})

        if action == "apply_patch":
            patch_text = kwargs.get("patch_text", "")
            if not patch_text:
                return ToolResult(success=False, error="'patch_text' is required")
            target_file = path if path.exists() else None

            if target_file and target_file.is_file():
                files_to_patch = {str(target_file): target_file}
            else:
                files_to_patch = {}
                for f in root.rglob("*"):
                    if f.is_file() and not self._is_ignored(f, root, patterns):
                        files_to_patch[str(f)] = f

            backup: dict[str, str] = {}
            patched = []
            errors = []

            file_chunks: dict[str, list[str]] = {}
            current_file = None
            for line in patch_text.splitlines(keepends=True):
                if line.startswith("--- "):
                    current_file = line[4:].strip()
                elif line.startswith("+++ "):
                    continue
                elif current_file and (line.startswith("@@") or line.startswith(" ") or line.startswith("+") or line.startswith("-")):
                    if current_file not in file_chunks:
                        file_chunks[current_file] = []
                    file_chunks[current_file].append(line)

            for filename, chunk in file_chunks.items():
                candidates = []
                fp = Path(filename)
                if fp.is_absolute():
                    candidates = [fp] if fp.exists() else []
                else:
                    key = str(fp)
                    if key in files_to_patch:
                        candidates = [files_to_patch[key]]
                    else:
                        candidates = [f for p, f in files_to_patch.items() if f.name == fp.name or str(fp) in p]

                if not candidates:
                    errors.append(f"File not found: {filename}")
                    continue

                target = candidates[0]
                try:
                    content = target.read_text(encoding="utf-8")
                    backup[str(target)] = content
                    lines = content.splitlines(keepends=True)
                except Exception as e:
                    errors.append(f"Cannot read {target}: {e}")
                    continue

                hunk_lines = [l for l in chunk if l.startswith("@@")]
                if not hunk_lines:
                    continue

                header = hunk_lines[0]
                match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
                if not match:
                    errors.append(f"Invalid hunk header in {filename}: {header.strip()}")
                    continue

                start_old = int(match.group(1))

                old_hunk = []
                new_hunk = []
                for l in chunk:
                    if l.startswith("-"):
                        old_hunk.append(l[1:])
                    elif l.startswith("+"):
                        new_hunk.append(l[1:])
                    elif l.startswith(" "):
                        old_hunk.append(l[1:])
                        new_hunk.append(l[1:])

                idx = start_old - 1
                found = False
                for attempt in range(max(1, len(lines) - len(old_hunk))):
                    window = lines[idx:idx + len(old_hunk)]
                    window_text = "".join(w.endswith("\n") and w or w + "\n" for w in window)
                    old_text_check = "".join(o.endswith("\n") and o or o + "\n" for o in old_hunk)
                    if window_text == old_text_check:
                        found = True
                        new_lines_list = lines[:idx] + [n if n.endswith("\n") else n + "\n" for n in new_hunk] + lines[idx + len(old_hunk):]
                        target.write_text("".join(new_lines_list), encoding="utf-8")
                        patched.append(str(target))
                        break
                    idx += 1

                if not found:
                    errors.append(f"Could not apply hunk in {filename} (lines {start_old})")

            if patched:
                result = f"Applied patch to {len(patched)} file(s):\n" + "\n".join(patched)
            else:
                result = ""
            if errors:
                if result:
                    result += "\n"
                result += "Errors:\n" + "\n".join(errors)

            if not patched and errors:
                for path_str, original in backup.items():
                    Path(path_str).write_text(original, encoding="utf-8")
                return ToolResult(success=False, error="Patch failed, rolled back:\n" + "\n".join(errors))

            return ToolResult(success=True, output=result or "Nothing to patch")

        return ToolResult(success=False, error=f"Unknown action: {action}")
