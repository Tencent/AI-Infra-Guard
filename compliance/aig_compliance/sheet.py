"""Build an xlsx of pass and fail cases. Question text stays out of the web page."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from io import BytesIO, StringIO

_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_HEADS = ("题号", "评测集", "结果", "判定", "对抗", "题目", "回答", "检查项")


def _xml(value: object) -> str:
    text = _ILLEGAL.sub("", str(value or ""))
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _cell(ref: str, value: object, style: int = 0) -> str:
    return f'<c r="{ref}" t="inlineStr" s="{style}"><is><t xml:space="preserve">{_xml(value)}</t></is></c>'


def workbook(rows: list[tuple]) -> bytes:
    body = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<cols>",
        '<col min="1" max="1" width="8"/>',
        '<col min="2" max="2" width="22"/>',
        '<col min="3" max="4" width="12"/>',
        '<col min="5" max="5" width="14"/>',
        '<col min="6" max="7" width="80"/>',
        '<col min="8" max="8" width="28"/>',
        "</cols>",
        "<sheetData>",
    ]
    letters = "ABCDEFGH"
    head = "".join(_cell(f"{letters[index]}1", name, 1) for index, name in enumerate(_HEADS))
    body.append(f'<row r="1">{head}</row>')
    for offset, item in enumerate(rows, start=2):
        number, dataset, result, mark, bypass, prompt, reply, checks = item
        style = 3 if result == "失败" else 2
        values = (number, dataset, result, mark, "绕过" if bypass else "", prompt, reply, _check_text(checks))
        cells = "".join(_cell(f"{letters[index]}{offset}", value, style if index == 2 else 0) for index, value in enumerate(values))
        body.append(f'<row r="{offset}">{cells}</row>')
    body.append("</sheetData></worksheet>")
    sheet = "".join(body)
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
    <font><sz val="11"/><color rgb="FF1F7A4D"/><name val="Calibri"/></font>
    <font><sz val="11"/><color rgb="FFB42318"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1D3A5F"/></patternFill></fill>
  </fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf/></cellStyleXfs>
  <cellXfs count="4">
    <xf/>
    <xf fontId="1" fillId="1" applyFont="1" applyFill="1"/>
    <xf fontId="2" applyFont="1"/>
    <xf fontId="3" applyFont="1"/>
  </cellXfs>
</styleSheet>"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as book:
        book.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>""",
        )
        book.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        book.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="题目明细" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        book.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>""",
        )
        book.writestr("xl/styles.xml", styles)
        book.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def _check_text(raw: object) -> str:
    try:
        rows = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return ""
    if not isinstance(rows, list):
        return ""
    parts = []
    for item in rows:
        if not isinstance(item, dict) or not item.get("hit"):
            continue
        parts.append(f"{item.get('id')}{'豁免' if item.get('exempt') else '命中'}")
    return "、".join(parts)


def _values(item: tuple) -> tuple:
    number, dataset, result, mark, bypass, prompt, reply, checks = item
    return (number, dataset, result, mark, "绕过" if bypass else "", prompt, reply, _check_text(checks))


def csv_bytes(rows: list[tuple]) -> bytes:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_HEADS)
    for item in rows:
        writer.writerow(_values(item))
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def jsonl_bytes(rows: list[tuple]) -> bytes:
    lines = []
    for item in rows:
        number, dataset, result, mark, bypass, prompt, reply, checks = item
        lines.append(json.dumps({
            "n": number,
            "set": dataset,
            "result": result,
            "mark": mark,
            "bypass": bool(bypass),
            "prompt": prompt,
            "reply": reply,
            "checks": _check_text(checks),
        }, ensure_ascii=False))
    return (("\n".join(lines) + "\n") if lines else "").encode("utf-8")
