import tempfile, os
import fitz  # pymupdf
import pytest
from chunkers.pdf import chunk_pdf


def _make_pdf(pages_text: list[str]) -> str:
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 50), text, fontsize=12)
    tmp_dir = tempfile.gettempdir()
    tmp_name = os.path.join(tmp_dir, f"test_pdf_{os.urandom(8).hex()}.pdf")
    doc.save(tmp_name)
    doc.close()
    return tmp_name


def test_chunk_pdf_at_least_one_chunk():
    path = _make_pdf(["Questo è un manuale di allenamento con principi di periodizzazione."])
    chunks = chunk_pdf(path)
    assert len(chunks) >= 1


def test_chunk_pdf_page_in_metadata():
    path = _make_pdf(["Prima pagina.", "Seconda pagina."])
    chunks = chunk_pdf(path)
    pages = {c["metadata"]["page"] for c in chunks}
    assert 1 in pages


def test_chunk_pdf_doc_type():
    path = _make_pdf(["Testo del manuale."])
    chunks = chunk_pdf(path)
    assert all(c["doc_type"] == "manual" for c in chunks)


def test_chunk_pdf_source():
    path = _make_pdf(["Contenuto."])
    chunks = chunk_pdf(path)
    assert chunks[0]["source"] == path


def test_chunk_pdf_no_empty_chunks():
    path = _make_pdf([""])
    chunks = chunk_pdf(path)
    assert all(c["content"].strip() for c in chunks)
