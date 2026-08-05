"""
odoo-bootstrap scaffold: Tạo module Odoo chuẩn OCA.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from odoo_bootstrap.core.constants import SUPPORTED_VERSIONS
from odoo_bootstrap.core.logger import get_logger

logger = get_logger("scaffold")
console = Console()


MANIFEST_TMPL = """{
    "name": "{name}",
    "summary": "{summary}",
    "version": "{version}.1.0.0",
    "category": "Uncategorized",
    "author": "BizApps",
    "license": "LGPL-3",
    "depends": {depends},
    "data": [
        "security/ir.model.access.csv",
        "views/{module}_views.xml",
        "views/{module}_menus.xml",
    ],
    "installable": True,
    "auto_install": False,
}
"""

MODEL_TMPL = """from odoo import fields, models


class {ClassName}(models.Model):
    _name = "{module_dotted}"
    _description = "{name}"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(default=True)
    notes = fields.Text(string="Notes")
"""

VIEW_TMPL = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- List View -->
    <record id="view_{module_name}_list" model="ir.ui.view">
        <field name="name">{module_dotted}.list</field>
        <field name="model">{module_dotted}</field>
        <field name="arch" type="xml">
            <list string="{name}">
                <field name="name"/>
            </list>
        </field>
    </record>

    <!-- Form View -->
    <record id="view_{module_name}_form" model="ir.ui.view">
        <field name="name">{module_dotted}.form</field>
        <field name="model">{module_dotted}</field>
        <field name="arch" type="xml">
            <form string="{name}">
                <sheet>
                    <group>
                        <field name="name"/>
                    </group>
                    <group>
                        <field name="notes"/>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <!-- Action -->
    <record id="action_{module_name}" model="ir.actions.act_window">
        <field name="name">{name}</field>
        <field name="res_model">{module_dotted}</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
"""

MENU_TMPL = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem
        id="menu_{module_name}_root"
        name="{name}"
        sequence="100"/>
    <menuitem
        id="menu_{module_name}"
        name="{name}"
        parent="menu_{module_name}_root"
        action="action_{module_name}"
        sequence="10"/>
</odoo>
"""

ACCESS_TMPL = """id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_{module_name}_user,{module_name}.user,model_{model_underscore},,1,0,0,0
access_{module_name}_manager,{module_name}.manager,model_{model_underscore},base.group_system,1,1,1,1
"""

TEST_TMPL = '''from odoo.tests import TransactionCase


class Test{ClassName}(TransactionCase):
    """Tests for {name}."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["{module_dotted}"]

    def test_create(self):
        record = self.Model.create({{"name": "Test"}})
        self.assertTrue(record.name)
'''

README_TMPL = """# {name}

{summary}

## Configuration

TODO

## Usage

TODO

## Known Issues / Roadmap

TODO

## Bug Tracker

TODO

## Credits

### Authors

* BizApps

### Contributors

TODO
"""


def run_scaffold(
    module_name: str,
    odoo_version: int,
    output_dir: Path,
    summary: str = "",
    depends: list[str] | None = None,
) -> None:
    """Tạo module Odoo chuẩn OCA."""

    if odoo_version not in SUPPORTED_VERSIONS:
        console.print(f"[red]Version {odoo_version} không hỗ trợ[/red]")
        return

    depends = depends or ["base"]
    module_dir = output_dir / module_name

    if module_dir.exists():
        console.print(f"[yellow]Module '{module_name}' đã tồn tại tại {module_dir}[/yellow]")
        return

    # Tên class từ module_name (snake_case → CamelCase)
    class_name = "".join(w.title() for w in module_name.split("_"))
    # model name: biz_contract → biz.contract
    module_dotted = module_name.replace("_", ".")
    # model field name: biz.contract → biz_contract
    model_underscore = module_name
    display_name = summary or " ".join(w.title() for w in module_name.split("_"))

    ctx = {
        "module": module_name,
        "module_name": module_name,
        "module_dotted": module_dotted,
        "model_underscore": model_underscore,
        "name": display_name,
        "summary": summary or display_name,
        "version": odoo_version,
        "depends": str(depends),
        "ClassName": class_name,
    }

    def write(rel_path: str, content: str) -> None:
        p = module_dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    # Tạo các file
    write("__manifest__.py", MANIFEST_TMPL.format(**ctx))
    write("__init__.py", "from . import models\n")
    write("models/__init__.py", f"from . import {module_name}\n")
    write(f"models/{module_name}.py", MODEL_TMPL.format(**ctx))
    write(f"views/{module_name}_views.xml", VIEW_TMPL.format(**ctx))
    write(f"views/{module_name}_menus.xml", MENU_TMPL.format(**ctx))
    write("security/ir.model.access.csv", ACCESS_TMPL.format(**ctx))
    write("tests/__init__.py", f"from . import test_{module_name}\n")
    write(f"tests/test_{module_name}.py", TEST_TMPL.format(**ctx))
    write("README.rst", README_TMPL.format(**ctx))
    write("static/description/index.html", f"<html><body><h1>{display_name}</h1></body></html>")

    console.print(
        f"[green bold]✓ Module '{module_name}' (Odoo {odoo_version}) tạo xong[/green bold]"
    )
    console.print(f"  Directory: [cyan]{module_dir}[/cyan]")
    console.print("\n  Files:")
    for f in sorted(module_dir.rglob("*")):
        if f.is_file():
            console.print(f"    [dim]{f.relative_to(module_dir)}[/dim]")
    console.print("\n  Tiếp theo:")
    console.print("  1. Copy vào custom_addons của project")
    console.print(f"  2. Paste {module_name}/models/{module_name}.py vào Claude để bổ sung fields")
    console.print("  3. Restart Odoo và install module")
