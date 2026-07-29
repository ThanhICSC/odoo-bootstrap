# odoo-bootstrap

Professional CLI toolkit for Odoo Partner development teams.

Built by BizApps — manages workspaces, projects, Docker images, backups, and more across Odoo 17, 18, and 19.

---

## Requirements

| Tool | Minimum | Notes |
|------|---------|-------|
| Ubuntu | 22.04+ | Tested on 26.04 LTS |
| Python | 3.12+ | |
| Docker Engine | 24+ | Already installed |
| Docker Compose | v2+ | Plugin form (`docker compose`) |
| Git | 2.x | |

---

## Installation

```bash
git clone https://github.com/bizapps/odoo-bootstrap.git
cd odoo-bootstrap
pip install -e .
```

Or install from a zip:

```bash
unzip odoo-bootstrap.zip
cd odoo-bootstrap
pip install -e .
```

Verify:

```bash
odoo-bootstrap --version
```

---

## Quick start

```bash
# 1. Check system health
odoo-bootstrap doctor

# 2. Initialize workspace (clones Odoo source, builds Docker images)
odoo-bootstrap init

# 3. Create a customer project on Odoo 19
odoo-bootstrap create-project customer_a --version 19

# 4. Start it
odoo-bootstrap start customer_a

# 5. Open browser
# http://localhost:8069
```

---

## Workspace layout

After `odoo-bootstrap init`, the following structure is created under `~/odoo-dev`:

```
~/odoo-dev/
├── versions/
│   ├── 17/
│   │   ├── source/        # git clone of odoo/odoo@17.0
│   │   ├── enterprise/    # copy your enterprise source here
│   │   ├── docker/        # generated Dockerfile + entrypoint.sh
│   │   └── config/
│   ├── 18/  ...
│   └── 19/  ...
├── projects/
│   └── customer_a/
│       ├── custom_addons/ # your custom modules go here
│       ├── filestore/     # Odoo filestore (attachments)
│       ├── backup/        # tar.gz backups
│       ├── logs/          # container logs
│       ├── config/
│       │   └── odoo.conf
│       ├── docker-compose.yml
│       ├── docker-compose.override.yml  # yours to edit
│       └── .env
├── shared/
│   └── docker-compose.yml  # postgres, pgadmin, mailpit, redis
├── backups/
├── logs/
├── Makefile
└── bootstrap.yaml          # main configuration file
```

---

## Commands

### `odoo-bootstrap init`

Initialize the full workspace.

```bash
odoo-bootstrap init
odoo-bootstrap init --skip-git          # skip git clone/pull
odoo-bootstrap init --skip-docker       # skip Docker image build
odoo-bootstrap init --versions 18,19    # only specific versions
```

Safe to run multiple times — fully idempotent.

---

### `odoo-bootstrap doctor`

System health check with colored output.

```bash
odoo-bootstrap doctor
```

Checks: Python, Docker, Docker Compose, Git, disk space, RAM, CPU, ports, workspace, Docker daemon, PostgreSQL, Python packages, projects, Docker images.

Exit code `1` if any error is found.

---

### `odoo-bootstrap status`

Show running containers, projects, ports.

```bash
odoo-bootstrap status
```

---

### `odoo-bootstrap create-project`

Create a new project for a customer.

```bash
odoo-bootstrap create-project customer_a --version 19
odoo-bootstrap create-project customer_b --version 18 --db-name custom_db_name
```

Creates: project directory, `odoo.conf`, `docker-compose.yml`, `.env`, override file, backup directory.

---

### `odoo-bootstrap remove-project`

Remove a project from configuration (with optional data deletion).

```bash
odoo-bootstrap remove-project customer_a
odoo-bootstrap remove-project customer_a --keep-data
```

---

### `odoo-bootstrap start` / `stop` / `restart`

```bash
odoo-bootstrap start customer_a
odoo-bootstrap stop customer_a
odoo-bootstrap restart customer_a
odoo-bootstrap restart customer_a --service odoo   # restart only odoo service
```

---

### `odoo-bootstrap logs`

```bash
odoo-bootstrap logs customer_a
odoo-bootstrap logs customer_a --follow
odoo-bootstrap logs customer_a --tail 200
```

---

### `odoo-bootstrap shell`

Open an Odoo interactive Python shell inside the container.

```bash
odoo-bootstrap shell customer_a
odoo-bootstrap shell customer_a --db my_other_db
```

---

### `odoo-bootstrap backup`

```bash
odoo-bootstrap backup customer_a
odoo-bootstrap backup customer_a --label pre_upgrade
```

Creates a `.tar.gz` archive containing: database dump, filestore, config. Stored in `projects/customer_a/backup/`.

---

### `odoo-bootstrap restore`

```bash
odoo-bootstrap restore customer_a ~/odoo-dev/projects/customer_a/backup/customer_a_20250101_120000.tar.gz
odoo-bootstrap restore customer_a archive.tar.gz --drop-existing
```

---

### `odoo-bootstrap update`

Git pull all Odoo sources and rebuild Docker images.

```bash
odoo-bootstrap update
odoo-bootstrap update 19     # only Odoo 19
```

---

### `odoo-bootstrap rebuild`

Force rebuild Docker images.

```bash
odoo-bootstrap rebuild
odoo-bootstrap rebuild 19
odoo-bootstrap rebuild 19 --no-cache
```

---

### `odoo-bootstrap clean`

Remove stopped containers and dangling images.

```bash
odoo-bootstrap clean
```

---

### `odoo-bootstrap requirements`

Install Python packages from `custom_addons/requirements.txt` inside running containers.

```bash
odoo-bootstrap requirements
odoo-bootstrap requirements customer_a
```

---

## Ports

| Service | Port |
|---------|------|
| Odoo 17 | 8067 |
| Odoo 18 | 8068 |
| Odoo 19 | 8069 |
| PgAdmin | 5050 |
| Mailpit (HTTP) | 8025 |
| Mailpit (SMTP) | 1025 |
| Redis | 6379 |

---

## Enterprise modules

Copy your Enterprise source into the version directory:

```bash
cp -r /path/to/enterprise ~/odoo-dev/versions/19/enterprise/
```

`odoo-bootstrap` automatically detects and includes it in `addons_path`.

---

## Custom modules

Place your modules in the project's `custom_addons` directory:

```bash
~/odoo-dev/projects/customer_a/custom_addons/
├── my_module/
│   ├── __manifest__.py
│   └── ...
└── requirements.txt   # optional Python deps
```

Version compatibility is checked automatically — a warning is shown if a module's declared Odoo version does not match the project version.

---

## VS Code integration

After `init`, `.vscode/` is created in the workspace root with:

- `launch.json` — debug configurations for each Odoo version
- `tasks.json` — quick-access tasks for start/stop/logs
- `settings.json` — Python path and formatter settings

---

## PyCharm setup

1. Open `~/odoo-dev` as a project.
2. Go to **Settings → Project → Python Interpreter → Add Interpreter → Docker**.
3. Select image `bizapps-odoo:19`.
4. Set working directory to `/opt/odoo/19.0`.
5. Add `/opt/odoo/19.0` and `/opt/custom_addons` to **Source Roots**.

---

## Adding Odoo 20

Edit `odoo_bootstrap/core/constants.py`:

```python
SUPPORTED_VERSIONS: list[int] = [17, 18, 19, 20]   # add 20 here

ODOO_PORTS: dict[int, int] = {
    17: 8067,
    18: 8068,
    19: 8069,
    20: 8070,                                        # add port here
}
```

That is the only change required. Re-run `odoo-bootstrap init --versions 20`.

---

## Makefile

A `Makefile` is generated at `~/odoo-dev/Makefile`:

```bash
cd ~/odoo-dev
make help
make start-customer_a
make stop-customer_a
make backup-customer_a
make doctor
make status
```

---

## License

MIT — see [LICENSE](LICENSE).
