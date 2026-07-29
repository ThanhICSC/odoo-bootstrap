"""
Jinja2-based template renderer for generating configuration files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from odoo_bootstrap.core.logger import get_logger

logger = get_logger("template_renderer")

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class TemplateRenderer:
    """Renders Jinja2 templates to strings or files."""

    def __init__(self, templates_dir: Path = TEMPLATES_DIR) -> None:
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template to a string."""
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_to_file(
        self,
        template_name: str,
        output_path: Path,
        context: dict[str, Any],
        overwrite: bool = True,
    ) -> bool:
        """Render a template and write to a file. Returns True if written."""
        if output_path.exists() and not overwrite:
            logger.debug(f"Skipping {output_path} (already exists)")
            return False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.render(template_name, context)
        output_path.write_text(content, encoding="utf-8")
        logger.debug(f"Rendered {template_name} → {output_path}")
        return True

    def render_string(self, template_str: str, context: dict[str, Any]) -> str:
        """Render a template from a string."""
        template = self.env.from_string(template_str)
        return template.render(**context)
