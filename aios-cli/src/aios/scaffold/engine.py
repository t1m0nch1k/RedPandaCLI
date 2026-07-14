from __future__ import annotations

import json
import os
import string
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TemplateInfo:
    name: str
    description: str
    version: str = "1.0.0"
    variables: list[dict[str, str]] = field(default_factory=list)
    path: str = ""
    source: str = "built-in"


def _gather_files(template_dir: Path) -> list[Path]:
    files = []
    for root, _dirs, filenames in os.walk(template_dir):
        for fn in filenames:
            if fn == "template.json":
                continue
            fp = Path(root) / fn
            rel = fp.relative_to(template_dir)
            # Skip hidden files in template dir root
            if rel.parts[0].startswith("."):
                continue
            files.append(fp)
    return files


def _render_path(template: str, variables: dict[str, str]) -> str:
    t = string.Template(template)
    return t.safe_substitute(**variables)


def _render_content(content: str, variables: dict[str, str]) -> str:
    t = string.Template(content)
    return t.safe_substitute(**variables)


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_template_info(template_dir: Path) -> TemplateInfo | None:
    meta_file = template_dir / "template.json"
    if not meta_file.exists():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    return TemplateInfo(
        name=meta.get("name", template_dir.name),
        description=meta.get("description", ""),
        version=meta.get("version", "1.0.0"),
        variables=meta.get("variables", []),
        path=str(template_dir),
    )


def scaffold_project(
    template_dir: Path,
    dest_dir: Path,
    variables: dict[str, str],
    force: bool = False,
) -> int:
    meta_file = template_dir / "template.json"
    if not meta_file.exists():
        return 0

    if dest_dir.exists() and not force:
        return -1

    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    var_defs = meta.get("variables", [])

    valid_vars: dict[str, str] = {}
    for v in var_defs:
        name = v.get("name", "")
        default = v.get("default", "")
        valid_vars[name] = variables.get(name, default)

    valid_vars.update(variables)

    files = _gather_files(template_dir)
    count = 0

    for src_path in files:
        rel = str(src_path.relative_to(template_dir))
        rendered_rel = _render_path(rel, valid_vars)

        if rendered_rel.startswith("."):
            continue

        content = src_path.read_text(encoding="utf-8")
        rendered_content = _render_content(content, valid_vars)

        dest_path = dest_dir / rendered_rel
        _write_file(dest_path, rendered_content)
        count += 1

    return count


class ScaffoldEngine:
    def __init__(self) -> None:
        self._built_in_dir = Path(__file__).parent / "templates"
        self._custom_dir = Path.home() / ".aios" / "templates"

    def list_templates(self) -> list[TemplateInfo]:
        results: list[TemplateInfo] = []

        if self._built_in_dir.exists():
            for child in sorted(self._built_in_dir.iterdir()):
                if child.is_dir():
                    info = load_template_info(child)
                    if info:
                        info.source = "built-in"
                        results.append(info)

        if self._custom_dir.exists():
            for child in sorted(self._custom_dir.iterdir()):
                if child.is_dir():
                    info = load_template_info(child)
                    if info:
                        info.source = "custom"
                        results.append(info)

        return results

    def get_template(self, name: str) -> Path | None:
        built_in = self._built_in_dir / name
        if built_in.exists() and (built_in / "template.json").exists():
            return built_in

        custom = self._custom_dir / name
        if custom.exists() and (custom / "template.json").exists():
            custom.mkdir(parents=True, exist_ok=True)
            return custom

        return None

    def scaffold(
        self,
        template_name: str,
        dest_dir: Path,
        variables: dict[str, str],
        force: bool = False,
    ) -> int:
        template_path = self.get_template(template_name)
        if template_path is None:
            return -2

        return scaffold_project(template_path, dest_dir, variables, force)
