"""
MARKER_155B.CANON.XLSX_CONVERTER.V1
MARKER_155B.CANON.MD_CONVERTER.V1
MARKER_155B.CANON.XML_CONVERTER.V1
MARKER_155B.CANON.CONVERT_API.V1

Canonical DAG converters for Phase 155B-P3.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Any, Dict, List, Tuple
from xml.etree import ElementTree as ET

from src.services.workflow_canonical_schema import (
    CURRENT_SCHEMA_VERSION,
    get_canonical_schema_template,
    validate_canonical_graph,
)


def _canonicalize_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    base = get_canonical_schema_template(str(payload.get("schema_version") or CURRENT_SCHEMA_VERSION))
    merged = dict(base)
    merged["schema_version"] = str(payload.get("schema_version") or CURRENT_SCHEMA_VERSION)
    for key in ("graph", "nodes", "edges", "layout_hints"):
        if key in payload:
            merged[key] = payload.get(key)
    result = validate_canonical_graph(merged)
    if not result.valid:
        raise ValueError(f"Invalid canonical graph: {result.errors}")
    return merged


def graph_to_markdown(payload: Dict[str, Any]) -> str:
    graph = _canonicalize_graph(payload)
    return (
        "# VETKA Canonical Graph\n\n"
        f"schema_version: {graph.get('schema_version', CURRENT_SCHEMA_VERSION)}\n\n"
        "## graph\n```json\n"
        f"{json.dumps(graph.get('graph', {}), ensure_ascii=False, indent=2)}\n```\n\n"
        "## nodes\n```json\n"
        f"{json.dumps(graph.get('nodes', []), ensure_ascii=False, indent=2)}\n```\n\n"
        "## edges\n```json\n"
        f"{json.dumps(graph.get('edges', []), ensure_ascii=False, indent=2)}\n```\n\n"
        "## layout_hints\n```json\n"
        f"{json.dumps(graph.get('layout_hints', {}), ensure_ascii=False, indent=2)}\n```\n"
    )


def graph_from_markdown(text: str) -> Dict[str, Any]:
    def _extract_json(section: str, default: Any) -> Any:
        pattern = rf"##\s*{re.escape(section)}\s*```json\s*(.*?)\s*```"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return default
        return json.loads(match.group(1).strip())

    schema_match = re.search(r"schema_version:\s*([0-9]+\.[0-9]+\.[0-9]+)", text, flags=re.IGNORECASE)
    payload = {
        "schema_version": schema_match.group(1) if schema_match else CURRENT_SCHEMA_VERSION,
        "graph": _extract_json("graph", {}),
        "nodes": _extract_json("nodes", []),
        "edges": _extract_json("edges", []),
        "layout_hints": _extract_json("layout_hints", {}),
    }
    return _canonicalize_graph(payload)


def graph_to_xml(payload: Dict[str, Any]) -> str:
    graph = _canonicalize_graph(payload)
    root = ET.Element("canonical_graph")
    root.set("schema_version", str(graph.get("schema_version") or CURRENT_SCHEMA_VERSION))

    for key in ("graph", "nodes", "edges", "layout_hints"):
        element = ET.SubElement(root, key)
        element.text = json.dumps(graph.get(key), ensure_ascii=False)

    return ET.tostring(root, encoding="unicode")


def graph_from_xml(text: str) -> Dict[str, Any]:
    root = ET.fromstring(text)
    if root.tag != "canonical_graph":
        raise ValueError("Invalid XML root: expected canonical_graph")
    payload = {
        "schema_version": str(root.attrib.get("schema_version") or CURRENT_SCHEMA_VERSION),
        "graph": {},
        "nodes": [],
        "edges": [],
        "layout_hints": {},
    }
    for key in ("graph", "nodes", "edges", "layout_hints"):
        el = root.find(key)
        if el is not None and (el.text or "").strip():
            payload[key] = json.loads((el.text or "").strip())
    return _canonicalize_graph(payload)


def _xlsx_cell_text(cell: ET.Element) -> str:
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    inline_t = cell.find(f"{ns}is/{ns}t")
    if inline_t is not None:
        return str(inline_t.text or "")
    value = cell.find(f"{ns}v")
    return str(value.text or "") if value is not None else ""


def _xlsx_sheet_rows(xml_text: str) -> List[Tuple[str, str, str]]:
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    root = ET.fromstring(xml_text)
    rows: List[Tuple[str, str, str]] = []
    for row in root.findall(f".//{ns}row"):
        col_vals = {"A": "", "B": "", "C": ""}
        for cell in row.findall(f"{ns}c"):
            ref = str(cell.attrib.get("r") or "")
            col = ref[:1]
            if col in col_vals:
                col_vals[col] = _xlsx_cell_text(cell)
        rows.append((col_vals["A"], col_vals["B"], col_vals["C"]))
    return rows


def graph_to_xlsx_bytes(payload: Dict[str, Any]) -> bytes:
    graph = _canonicalize_graph(payload)

    rows: List[Tuple[str, str, str]] = [
        ("section", "key", "value"),
        ("graph", "schema_version", str(graph.get("schema_version") or CURRENT_SCHEMA_VERSION)),
        ("graph", "graph", json.dumps(graph.get("graph", {}), ensure_ascii=False)),
        ("graph", "layout_hints", json.dumps(graph.get("layout_hints", {}), ensure_ascii=False)),
    ]
    for node in graph.get("nodes", []):
        rows.append(("node", str(node.get("id") or ""), json.dumps(node, ensure_ascii=False)))
    for edge in graph.get("edges", []):
        edge_key = f"{edge.get('source', '')}->{edge.get('target', '')}"
        rows.append(("edge", edge_key, json.dumps(edge, ensure_ascii=False)))

    def _cell_xml(col: str, row_idx: int, value: str) -> str:
        safe = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        ref = f"{col}{row_idx}"
        return f'<c r="{ref}" t="inlineStr"><is><t>{safe}</t></is></c>'

    row_xml_parts: List[str] = []
    for idx, (a, b, c) in enumerate(rows, start=1):
        row_xml_parts.append(
            f'<row r="{idx}">{_cell_xml("A", idx, a)}{_cell_xml("B", idx, b)}{_cell_xml("C", idx, c)}</row>'
        )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(row_xml_parts)
        + "</sheetData></worksheet>"
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="canonical_graph" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def graph_from_xlsx_bytes(data: bytes) -> Dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            sheet_bytes = zf.read("xl/worksheets/sheet1.xml")
    except Exception as e:
        raise ValueError(f"Invalid XLSX payload: {e}")

    rows = _xlsx_sheet_rows(sheet_bytes.decode("utf-8"))
    payload = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "graph": {},
        "nodes": [],
        "edges": [],
        "layout_hints": {},
    }

    for idx, (section, key, value) in enumerate(rows):
        if idx == 0 and section == "section":
            continue
        if section == "graph":
            if key == "schema_version":
                payload["schema_version"] = value or CURRENT_SCHEMA_VERSION
            elif key == "graph":
                payload["graph"] = json.loads(value or "{}")
            elif key == "layout_hints":
                payload["layout_hints"] = json.loads(value or "{}")
        elif section == "node":
            payload["nodes"].append(json.loads(value or "{}"))
        elif section == "edge":
            payload["edges"].append(json.loads(value or "{}"))

    return _canonicalize_graph(payload)
