from __future__ import annotations

from aios.scaffold.engine import ScaffoldEngine, TemplateInfo

_engine: ScaffoldEngine | None = None


def get_engine() -> ScaffoldEngine:
    global _engine
    if _engine is None:
        _engine = ScaffoldEngine()
    return _engine


def get_template_registry() -> list[TemplateInfo]:
    return get_engine().list_templates()


def get_template(name: str) -> TemplateInfo | None:
    for t in get_template_registry():
        if t.name == name:
            return t
    return None
