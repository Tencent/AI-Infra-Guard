from pathlib import Path

from mcp_scan.tools.registry import _load_xml_schema


def test_load_xml_schema_forces_utf8(tmp_path, monkeypatch):
    schema = tmp_path / "schema.xml"
    schema.write_text(
        '<tools><tool name="demo"><description>中文描述</description></tool></tools>',
        encoding="utf-8",
    )

    original = Path.read_text

    def read_text(path, encoding=None, errors=None):
        assert encoding == "utf-8", "schemas must be read as UTF-8 regardless of locale"
        return original(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", read_text)

    tools = _load_xml_schema(schema)
    assert "demo" in tools
    assert "中文描述" in tools["demo"]
