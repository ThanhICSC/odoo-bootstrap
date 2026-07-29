"""Unit tests for TemplateRenderer."""

import pytest

from odoo_bootstrap.config.template_renderer import TemplateRenderer


@pytest.fixture
def renderer():
    return TemplateRenderer()


def test_render_string_simple(renderer):
    result = renderer.render_string("Hello {{ name }}!", {"name": "Odoo"})
    assert result == "Hello Odoo!"


def test_render_string_list(renderer):
    result = renderer.render_string(
        "{% for item in items %}{{ item }},{% endfor %}",
        {"items": ["a", "b", "c"]},
    )
    assert "a,b,c," in result


def test_render_to_file(tmp_path, renderer):
    # Use the string rendering approach to test file output
    output = tmp_path / "test.txt"
    tpl_content = "version={{ version }}"
    # Use temp template dir
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "test.j2").write_text(tpl_content)

    local_renderer = TemplateRenderer(templates_dir=tpl_dir)
    written = local_renderer.render_to_file("test.j2", output, {"version": 19})
    assert written is True
    assert output.read_text() == "version=19"


def test_render_to_file_no_overwrite(tmp_path):
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "tpl.j2").write_text("new content")
    output = tmp_path / "out.txt"
    output.write_text("original")

    renderer = TemplateRenderer(templates_dir=tpl_dir)
    written = renderer.render_to_file("tpl.j2", output, {}, overwrite=False)
    assert written is False
    assert output.read_text() == "original"


def test_render_real_odoo_conf_template(renderer):
    """Test the real odoo.conf template renders without errors."""
    from odoo_bootstrap.core.models import DatabaseConfig, OdooConfig

    db = DatabaseConfig(host="postgres", port=5432, user="odoo", password="odoo", name="test_db")
    odoo = OdooConfig()
    content = renderer.render(
        "odoo/odoo.conf.j2",
        {
            "version": 19,
            "project_name": "test_project",
            "db": db,
            "odoo": odoo,
            "addons_path": ["/opt/odoo", "/opt/custom"],
        },
    )
    assert "db_host = postgres" in content
    assert "db_name = test_db" in content
    assert "workers = 0" in content
