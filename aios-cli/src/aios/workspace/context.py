from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceContext:
    root: Path

    @classmethod
    def from_cwd(cls) -> WorkspaceContext:
        return cls(Path.cwd())

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.expanduser().resolve())

    def resolve_path(self, path: str | Path = ".") -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        return candidate.resolve(strict=False)

    def contains(self, path: str | Path) -> bool:
        candidate = self.resolve_path(path)
        return candidate == self.root or self.root in candidate.parents

    def require_path(self, path: str | Path = ".") -> Path:
        candidate = self.resolve_path(path)
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError(f"Path is outside workspace: {path}")
        return candidate

    def display_path(self, path: str | Path) -> str:
        candidate = self.resolve_path(path)
        try:
            return str(candidate.relative_to(self.root))
        except ValueError:
            return str(candidate)
