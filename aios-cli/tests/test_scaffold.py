from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from aios.scaffold.engine import ScaffoldEngine, load_template_info


@pytest.fixture
def engine():
    return ScaffoldEngine()


def test_list_templates(engine):
    templates = engine.list_templates()
    names = [t.name for t in templates]
    assert "python-package" in names
    assert "cli-app" in names
    assert "plugin" in names


def test_get_template(engine):
    tp = engine.get_template("python-package")
    assert tp is not None
    assert (tp / "template.json").exists()

    tp2 = engine.get_template("nonexistent")
    assert tp2 is None


def test_load_template_info(engine):
    tp = engine.get_template("python-package")
    info = load_template_info(tp)
    assert info is not None
    assert info.name == "python-package"
    assert info.description
    assert len(info.variables) > 0
    assert info.variables[0]["name"] == "project_name"


def test_scaffold_python_package(engine):
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "my_pkg"
        count = engine.scaffold("python-package", dest, {
            "project_name": "my_pkg",
            "description": "Test",
            "author": "Tester",
        })
        assert count > 0
        assert (dest / "README.md").exists()
        assert (dest / "pyproject.toml").exists()
        assert (dest / "src" / "my_pkg" / "__init__.py").exists()
        assert (dest / "tests" / "test_main.py").exists()

        readme = (dest / "README.md").read_text()
        assert "my_pkg" in readme
        assert "Test" in readme


def test_scaffold_cli_app(engine):
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "my_cli"
        count = engine.scaffold("cli-app", dest, {
            "project_name": "my_cli",
            "description": "CLI test",
            "author": "Tester",
        })
        assert count > 0
        assert (dest / "src" / "my_cli" / "cli.py").exists()
        cli_content = (dest / "src" / "my_cli" / "cli.py").read_text()
        assert "my_cli" in cli_content


def test_scaffold_plugin(engine):
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "my_plugin"
        count = engine.scaffold("plugin", dest, {
            "plugin_name": "my_plugin",
            "description": "Test plugin",
            "author": "Tester",
            "version": "1.0.0",
        })
        assert count > 0
        assert (dest / "plugin.py").exists()
        content = (dest / "plugin.py").read_text()
        assert "my_plugin" in content
        assert "my_pluginTool" in content
        assert "my_pluginPlugin" in content


def test_scaffold_unknown_template(engine):
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "x"
        count = engine.scaffold("nonexistent", dest, {})
        assert count == -2


def test_scaffold_existing_dir(engine):
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "existing"
        dest.mkdir()
        count = engine.scaffold("python-package", dest, {}, force=False)
        assert count == -1

        count2 = engine.scaffold("python-package", dest, {}, force=True)
        assert count2 > 0
