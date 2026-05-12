import tempfile, os
from docx import Document as DocxDocument
import pytest
from chunkers.docx import chunk_docx


def _make_docx(paragraphs: list[tuple[str, str]]) -> str:
    """paragraphs: list of (style, text). Style: 'Normal' | 'Heading 1' | ..."""
    doc = DocxDocument()
    for style, text in paragraphs:
        doc.add_paragraph(text, style=style)
    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    doc.save(tmp.name)
    tmp.close()
    return tmp.name


def test_chunk_docx_basic():
    path = _make_docx([
        ("Heading 1", "Struttura Scheda"),
        ("Normal", "La scheda deve avere un riscaldamento di 10 minuti."),
        ("Normal", "Seguono gli esercizi principali."),
    ])
    chunks = chunk_docx(path)
    assert len(chunks) >= 1


def test_chunk_docx_section_in_metadata():
    path = _make_docx([
        ("Heading 1", "Progressione"),
        ("Normal", "Aumenta il carico del 5% ogni 2 settimane."),
    ])
    chunks = chunk_docx(path)
    assert chunks[0]["metadata"]["section"] == "Progressione"


def test_chunk_docx_doc_type():
    path = _make_docx([
        ("Normal", "Contenuto senza heading."),
    ])
    chunks = chunk_docx(path)
    assert all(c["doc_type"] == "guideline" for c in chunks)


def test_chunk_docx_source():
    path = _make_docx([
        ("Heading 1", "Test"),
        ("Normal", "Testo di test per verificare il campo source."),
    ])
    chunks = chunk_docx(path)
    assert chunks[0]["source"] == path
