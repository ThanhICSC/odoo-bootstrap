# Architecture Guide

## Overview

`odoo-bootstrap` follows a layered, modular architecture built for long-term maintenance by a small partner team.

```
┌─────────────────────────────────────────────────────┐
│                   CLI Layer (Typer)                 │
│              odoo_bootstrap/main.py                 │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│               Commands Layer                        │
│  cmd_init  cmd_doctor  cmd_project  cmd_backup      │
│  cmd_status  cmd_service                            │
└───────┬───────────────┬─────────────────────────────┘
        │               │
┌───────▼───────┐ ┌─────▼──────────────────────────────┐
│  Core Layer   │ │         Service Layer               │
│  models       │ │  DockerService  TemplateRenderer    │
│  config_mgr   │ │                                     │
│  constants    │ └─────────────────────────────────────┘
│  exceptions   │
│  logger       │ ┌─────────────────────────────────────┐
└───────────────┘ │         Utils Layer                 │
                  │  system  git  database  addon        │
                  └─────────────────────────────────────┘
```

---

## Layer responsibilities

### CLI Layer (`main.py`)

- Declares all `typer` commands.
- Handles argument parsing and option defaults.
- Delegates entirely to the Commands layer — no business logic here.
- Manages the shared `ConfigManager` singleton.

### Commands Layer (`commands/`)

Each file owns one command or a closely related group:

| File | Commands |
|------|----------|
| `cmd_init.py` | `init` |
| `cmd_doctor.py` | `doctor` |
| `cmd_project.py` | `create-project`, `remove-project` |
| `cmd_backup.py` | `backup`, `restore` |
| `cmd_status.py` | `status` |
| `cmd_service.py` | `start`, `stop`, `restart`, `logs`, `shell`, `rebuild`, `clean`, `update`, `requirements` |

Commands receive a `ConfigManager` instance — they do not instantiate it themselves (dependency injection).

### Core Layer (`core/`)

Pure domain objects with no side effects:

- `constants.py` — single source of truth for versions, ports, paths.
- `models.py` — Pydantic models (`ProjectConfig`, `BootstrapConfig`, `DoctorReport`, etc.).
- `config_manager.py` — load/save `bootstrap.yaml`.
- `exceptions.py` — typed exception hierarchy.
- `logger.py` — Rich-based logging setup.

### Service Layer (`docker/`, `config/`)

- `DockerService` — wraps the Docker SDK. All Docker calls go through here.
- `TemplateRenderer` — wraps Jinja2. All file generation goes through here.

### Utils Layer (`utils/`)

- `system.py` — OS-level checks (disk, RAM, CPU, ports, commands).
- `git.py` — clone/pull operations.
- `database.py` — PostgreSQL operations via psycopg2 and pg_dump/pg_restore.
- `addon.py` — `__manifest__.py` parsing and version compatibility.

---

## Configuration flow

```
bootstrap.yaml (YAML)
      │
      ▼
ConfigManager.load()
      │
      ▼
BootstrapConfig (Pydantic)
      │
      ├── projects: dict[str, ProjectConfig]
      ├── versions: list[int]
      └── service flags (enable_pgadmin, etc.)
```

`bootstrap.yaml` lives at `~/odoo-dev/bootstrap.yaml`. It is created automatically on first save and safe to edit by hand.

---

## Template system

All generated files are Jinja2 templates in `odoo_bootstrap/templates/`:

```
templates/
├── docker/
│   ├── Dockerfile.j2
│   └── entrypoint.sh.j2
├── odoo/
│   └── odoo.conf.j2
├── compose/
│   ├── docker-compose.yml.j2
│   └── docker-compose.override.yml.j2
├── project/
│   └── env.j2
├── vscode/
│   ├── launch.json.j2
│   ├── tasks.json.j2
│   └── settings.json.j2
└── shared/
    ├── docker-compose.shared.yml.j2
    ├── init-db.sh.j2
    └── Makefile.j2
```

`TemplateRenderer.render_to_file()` accepts an `overwrite` flag:
- `overwrite=True` (default) — always regenerate (config files, Dockerfiles).
- `overwrite=False` — skip if exists (user-editable files like `docker-compose.override.yml`).

---

## Idempotency

Every operation is designed to be safe to run multiple times:

- Directory creation uses `mkdir(parents=True, exist_ok=True)`.
- Git operations use `clone_or_pull()` which pulls if already cloned.
- Docker image builds check `image_exists()` before building.
- Database creation checks `database_exists()` before creating.
- Project creation uses `overwrite=False` for user-editable files.

---

## Adding a new command

1. Create `odoo_bootstrap/commands/cmd_mycommand.py` with a `run_mycommand()` function.
2. Add a `@app.command("my-command")` entry in `main.py`.
3. Add a test in `tests/unit/test_mycommand.py`.
4. Add a Makefile target in `templates/shared/Makefile.j2`.

---

## Adding Odoo 20

Edit `odoo_bootstrap/core/constants.py` only:

```python
SUPPORTED_VERSIONS: list[int] = [17, 18, 19, 20]
ODOO_PORTS: dict[int, int] = {17: 8067, 18: 8068, 19: 8069, 20: 8070}
```

Everything else — loops, Dockerfile generation, compose files, doctor checks — picks up the new version automatically.

---

## Dependency injection

`ConfigManager` is created once in `main.py` via `get_config_manager()` and passed as a parameter to every command function. This makes commands testable without file I/O — tests can inject a `ConfigManager` backed by a `tmp_path` fixture.

---

## Error handling

All domain errors derive from `BootstrapError`:

```
BootstrapError
├── ConfigurationError
├── DockerError
├── GitError
├── DatabaseError
├── ProjectError
├── VersionError
├── BackupError
└── DependencyError
```

Commands catch these and print a user-friendly `[red]` message via Rich before exiting with a non-zero code.
