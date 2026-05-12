import io
import openpyxl
import pytest
from chunkers.excel import chunk_excel


def _make_xlsx(rows: list[dict]) -> str:
    """Crea un file Excel temporaneo in-memory e salvalo su disco."""
    import tempfile, os
    wb = openpyxl.Workbook()
    ws = wb.active
    if not rows:
        return ""
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()
    return tmp.name


def test_chunk_excel_one_row_per_exercise():
    path = _make_xlsx([
        {"Nome": "Panca Piana", "Muscoli": "Petto, Tricipiti", "Attrezzatura": "Bilanciere", "Difficolta": "Intermedio"},
        {"Nome": "Squat", "Muscoli": "Quadricipiti, Glutei", "Attrezzatura": "Bilanciere", "Difficolta": "Avanzato"},
    ])
    chunks = chunk_excel(path)
    assert len(chunks) == 2


def test_chunk_excel_content_includes_name():
    path = _make_xlsx([
        {"Nome": "Curl Bicipiti", "Muscoli": "Bicipiti", "Attrezzatura": "Manubri", "Difficolta": "Base"},
    ])
    chunks = chunk_excel(path)
    assert "Curl Bicipiti" in chunks[0]["content"]


def test_chunk_excel_metadata_fields():
    path = _make_xlsx([
        {"Nome": "Lat Machine", "Muscoli": "Dorsali, Bicipiti", "Attrezzatura": "Cavo", "Difficolta": "Base"},
    ])
    chunks = chunk_excel(path)
    meta = chunks[0]["metadata"]
    assert meta["doc_type"] == "exercise"
    assert isinstance(meta["muscles"], list)
    assert "Dorsali" in meta["muscles"]


def test_chunk_excel_source_field():
    path = _make_xlsx([
        {"Nome": "Plank", "Muscoli": "Core", "Attrezzatura": "Nessuna", "Difficolta": "Base"},
    ])
    chunks = chunk_excel(path)
    assert chunks[0]["source"] == path
    assert chunks[0]["doc_type"] == "exercise"
