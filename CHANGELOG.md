# Changelog

All notable changes to odoo-bootstrap are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.0] — 2025-07-29

### Added

- Full workspace initialization (`odoo-bootstrap init`)
- System health checker (`odoo-bootstrap doctor`) with 15+ checks
- Project management (`create-project`, `remove-project`)
- Service management (`start`, `stop`, `restart`, `logs`, `shell`)
- Docker image management (`rebuild`, `clean`, `update`)
- Backup and restore (`backup`, `restore`) with tar.gz archives
- Status dashboard (`status`) for containers, projects, and ports
- Python requirements installer (`requirements`)
- Custom Dockerfile generation per Odoo version (17, 18, 19)
- Jinja2 template system for all generated files
- Pydantic v2 configuration models
- YAML-based `bootstrap.yaml` configuration
- VS Code `launch.json`, `tasks.json`, `settings.json` generation
- Makefile generation per workspace
- Shared infrastructure compose (PostgreSQL, PgAdmin, Mailpit, Redis, Adminer)
- Odoo `__manifest__.py` parser with version compatibility checker
- Git clone/pull with shallow clone support
- Idempotent operations throughout
- Rich-based colored terminal output
- Unit tests for all core modules
- Integration tests for CLI commands
- GitHub Actions CI workflow
- Architecture and Developer guides
- PyCharm setup documentation

---

## Planned

- `odoo-bootstrap scaffold` — generate a new custom module skeleton
- `odoo-bootstrap upgrade` — run Odoo database upgrade with migration
- Multi-instance project support (multiple Odoo services per compose)
- Nginx reverse proxy template generation
- SSL certificate setup via Certbot
- Odoo 20 support (add version to constants only)
