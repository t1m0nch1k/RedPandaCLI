from pathlib import Path

import pytest
from aios.tools.filesystem import FilesystemTool
from aios.workspace import WorkspaceContext


@pytest.mark.asyncio
async def test_filesystem_create_and_delete(tmp_path: Path):
    tool = FilesystemTool(WorkspaceContext(tmp_path))
    target = tmp_path / "test_dir"

    result = await tool.run(action="create_folder", path=str(target))
    assert result.success
    assert target.exists()

    result = await tool.run(action="delete", path=str(target))
    assert result.success
    assert not target.exists()


@pytest.mark.asyncio
async def test_filesystem_rejects_paths_outside_workspace(tmp_path: Path):
    tool = FilesystemTool(WorkspaceContext(tmp_path))
    outside = tmp_path.parent / "outside.txt"

    result = await tool.run(action="create_file", path=str(outside), content="nope")

    assert not result.success
    assert "outside workspace" in result.error


@pytest.mark.asyncio
async def test_filesystem_replace_text_requires_unique_match(tmp_path: Path):
    tool = FilesystemTool(WorkspaceContext(tmp_path))
    target = tmp_path / "example.txt"
    target.write_text("same\nsame\n", encoding="utf-8")

    result = await tool.run(action="replace_text", path=str(target), old_text="same", new_text="changed")

    assert not result.success
    assert "make it more specific" in result.error
    assert target.read_text(encoding="utf-8") == "same\nsame\n"
