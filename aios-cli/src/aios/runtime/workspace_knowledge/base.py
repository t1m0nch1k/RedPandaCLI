from __future__ import annotations

from pathlib import Path

from aios.runtime.models import (
    CommitInfo,
    DependencyGraph,
    EntryPoint,
    FileEntry,
    FrameworkInfo,
    GitContext,
    PackageManager,
    SearchResult,
    SymbolLocation,
    TestConfig,
)


class WorkspaceKnowledgeProtocol:
    """
    Comprehensive workspace intelligence service providing contextual
    understanding of the project that the agent is operating on.

    Provides symbol indexing, file map, repository context, dependency
    detection, framework detection, git history, and entry point discovery.
    """

    async def build_index(self) -> None:
        """Full knowledge base rebuild. Runs in background thread."""

    async def query_symbol(self, symbol: str) -> list[SymbolLocation]:
        """Find all locations of a symbol across the workspace."""

    async def file_context(
        self,
        path: str,
        start_line: int = 0,
        end_line: int | None = None,
    ) -> str:
        """Read a range of lines from a file with line numbers."""

    async def repo_map(self, max_tokens: int = 1_024) -> str:
        """Generate a compact repository map (file tree + key symbols) for LLM context."""

    async def search_text(
        self,
        pattern: str,
        include: str | None = None,
    ) -> list[SearchResult]:
        """Regex search across workspace files."""

    async def list_directory(self, path: str = ".") -> list[FileEntry]:
        """List files and directories in a workspace path."""

    @property
    def workspace_root(self) -> Path:
        """Return the absolute path to the workspace root."""

    async def detect_frameworks(self) -> list[FrameworkInfo]:
        """Detect project frameworks from config files and package manifests."""

    async def dependency_graph(self) -> DependencyGraph:
        """Parse package manager files into a dependency graph."""

    async def package_managers(self) -> list[PackageManager]:
        """Detect which package managers are in use and their config paths."""

    async def test_config(self) -> TestConfig | None:
        """Detect test framework configuration."""

    async def entry_points(self) -> list[EntryPoint]:
        """Find likely project entry points."""

    async def git_context(self) -> GitContext:
        """Provide git state: current branch, recent commits, staged/unstaged changes."""

    async def git_history(
        self,
        path: str | None = None,
        max_commits: int = 20,
    ) -> list[CommitInfo]:
        """Recent commit history for a file or the entire project."""
