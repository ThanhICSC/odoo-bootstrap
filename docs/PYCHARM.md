# PyCharm Setup Guide

## Docker-based interpreter (recommended)

This gives you a Python interpreter running inside the custom Odoo Docker image, so all Odoo modules are importable.

### Step 1 — Build the image

```bash
odoo-bootstrap init --skip-git   # or full init if first time
```

Verify the image exists:

```bash
docker images | grep bizapps-odoo
```

### Step 2 — Add Docker interpreter in PyCharm

1. Open **Settings** (`Ctrl+Alt+S`).
2. Go to **Project → Python Interpreter**.
3. Click the gear icon → **Add Interpreter → On Docker**.
4. Select **Image name**: `bizapps-odoo:19` (or 18 / 17).
5. Click **OK**.

### Step 3 — Set source roots

In **Project** panel, right-click each directory and choose **Mark Directory as → Sources Root**:

- `~/odoo-dev/versions/19/source`
- `~/odoo-dev/versions/19/enterprise` (if present)
- `~/odoo-dev/projects/customer_a/custom_addons`

### Step 4 — Run/Debug configuration

1. Go to **Run → Edit Configurations → Add → Python**.
2. Set:
   - **Script**: `~/odoo-dev/versions/19/source/odoo-bin`
   - **Parameters**: `--config=/path/to/odoo.conf --dev=reload,qweb,xml --log-level=debug`
   - **Interpreter**: the Docker interpreter added above
3. Save and use **Debug** (`Shift+F9`) for breakpoint debugging.

---

## Local interpreter (alternative)

If you prefer a local venv:

```bash
cd ~/odoo-dev/versions/19/source
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install psycopg2-binary Pillow lxml openpyxl
```

In PyCharm, set the interpreter to `~/odoo-dev/versions/19/source/.venv/bin/python`.

---

## Useful PyCharm plugins

- **Odoo** — syntax highlighting for XML views, domain expressions.
- **Rainbow Brackets** — easier to read nested Odoo domains.
- **EnvFile** — load `.env` files into run configurations automatically.

---

## PostgreSQL datasource

1. Open **Database** panel → **+** → **Data Source → PostgreSQL**.
2. Set:
   - Host: `localhost`
   - Port: `5432`
   - User: `odoo`
   - Password: `odoo`
   - Database: `odoo_customer_a_19` (or your project DB name)
3. Click **Test Connection**.

---

## Recommended `.idea/` settings (`.gitignore`)

Add to your project `.gitignore`:

```
.idea/
*.iml
```

Each developer configures their own PyCharm workspace locally.
