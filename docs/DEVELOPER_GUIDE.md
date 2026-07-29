# Developer Guide

## Setup for development

```bash
git clone https://github.com/bizapps/odoo-bootstrap.git
cd odoo-bootstrap
pip install -e ".[dev]"
```

---

## Run tests

```bash
# All tests
pytest

# Unit tests only (no Docker needed)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage report
pytest --cov=odoo_bootstrap --cov-report=term-missing
```

---

## Code style

```bash
# Format
black .

# Sort imports
isort .

# Lint
ruff check .

# Type check
mypy odoo_bootstrap/
```

All four tools are configured in `pyproject.toml`. The CI pipeline enforces them on every push.

---

## Project structure

```
odoo_bootstrap/
├── __init__.py          # version string
├── main.py              # CLI entry point
├── core/
│   ├── constants.py     # all version/port/path constants
│   ├── models.py        # Pydantic data models
│   ├── config_manager.py
│   ├── logger.py
│   └── exceptions.py
├── docker/
│   └── docker_service.py
├── config/
│   └── template_renderer.py
├── commands/
│   ├── cmd_init.py
│   ├── cmd_doctor.py
│   ├── cmd_project.py
│   ├── cmd_backup.py
│   ├── cmd_status.py
│   └── cmd_service.py
├── utils/
│   ├── system.py
│   ├── git.py
│   ├── database.py
│   └── addon.py
└── templates/
    ├── docker/
    ├── odoo/
    ├── compose/
    ├── project/
    ├── vscode/
    └── shared/
```

---

## Writing a new command

### Step 1 — Command function

Create `odoo_bootstrap/commands/cmd_myfeature.py`:

```python
from rich.console import Console
from odoo_bootstrap.core.logger import get_logger

logger = get_logger("myfeature")
console = Console()


def run_myfeature(name: str, config_manager) -> None:
    project = config_manager.get_project(name)
    if not project:
        from odoo_bootstrap.core.exceptions import ProjectError
        raise ProjectError(f"Project '{name}' not found")

    # your logic here
    console.print(f"[green]✓ Done for {name}[/green]")
```

### Step 2 — Register in main.py

```python
@app.command("my-feature")
def cmd_myfeature(
    name: str = typer.Argument(..., help="Project name."),
) -> None:
    """Short description shown in --help."""
    from odoo_bootstrap.commands.cmd_myfeature import run_myfeature
    run_myfeature(name=name, config_manager=get_config_manager())
```

### Step 3 — Write tests

```python
# tests/unit/test_myfeature.py
def test_run_myfeature(tmp_path):
    from odoo_bootstrap.core.config_manager import ConfigManager
    from odoo_bootstrap.core.models import ProjectConfig
    from odoo_bootstrap.commands.cmd_myfeature import run_myfeature

    cfg = ConfigManager(config_path=tmp_path / "bootstrap.yaml")
    cfg.add_project(ProjectConfig(name="test", version=19))
    run_myfeature("test", cfg)
```

---

## Writing a new Jinja2 template

1. Create `odoo_bootstrap/templates/<category>/mytemplate.j2`.
2. Call it from a command:

```python
renderer = TemplateRenderer()
renderer.render_to_file(
    "category/mytemplate.j2",
    output_path,
    context={"key": "value"},
    overwrite=True,
)
```

Use `overwrite=False` for files the user is expected to customize.

---

## Testing templates

```python
def test_my_template(renderer):
    content = renderer.render("category/mytemplate.j2", {"key": "value"})
    assert "expected string" in content
```

---

## ConfigManager in tests

Always use a `tmp_path`-backed `ConfigManager` in tests — never the real `~/odoo-dev/bootstrap.yaml`:

```python
@pytest.fixture
def cfg(tmp_path):
    return ConfigManager(config_path=tmp_path / "bootstrap.yaml")
```

---

## Docker in tests

Unit tests must not require Docker. Use `pytest-mock` to mock `DockerService`:

```python
def test_something(mocker):
    mocker.patch(
        "odoo_bootstrap.docker.docker_service.DockerService.image_exists",
        return_value=True,
    )
```

Integration tests that do need Docker are tagged `@pytest.mark.integration` and skipped in CI unless Docker is available.

---

## Release process

1. Bump version in `odoo_bootstrap/__init__.py` and `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Push to `main`.
4. CI builds, lints, and tests automatically.
5. Tag: `git tag v1.x.x && git push --tags`.
6. Build ZIP: `make zip` (see Makefile).

---

## Environment variables

No environment variables are required. All configuration is in `bootstrap.yaml` and `.env` files inside project directories.

Optional overrides for the CLI itself:

| Variable | Default | Description |
|----------|---------|-------------|
| `BOOTSTRAP_WORKSPACE` | `~/odoo-dev` | Workspace root override |
| `BOOTSTRAP_LOG_LEVEL` | `INFO` | Log level |

---

## Logging

Use `get_logger(__name__)` — never `print()` in library code:

```python
from odoo_bootstrap.core.logger import get_logger
logger = get_logger("my_module")

logger.debug("Detailed step")
logger.info("Normal progress")
logger.warning("Something unusual")
logger.error("Something failed")
```

Use Rich `console.print()` only in command functions for user-facing output.
