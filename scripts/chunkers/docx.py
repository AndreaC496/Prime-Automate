import tiktoken
from docx import Document as DocxDocument

_HEADING_STYLES = {"heading 1", "heading 2", "heading 3", "titolo 1", "titolo 2"}
_ENC = tiktoken.get_encoding("cl100k_base")


def _split_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")
    tokens = _ENC.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(_ENC.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start += chunk_size - overlap
    return chunks


def chunk_docx(filepath: str, chunk_size: int = 300, overlap: int = 50) -> list[dict]:
    doc = DocxDocument(filepath)
    chunks = []
    current_section = ""
    current_text = ""

    def flush(section: str, text: str) -> None:
        text = text.strip()
        if not text:
            return
        for part in _split_tokens(text, chunk_size, overlap):
            if part.strip():
                chunks.append({
                    "content": part.strip(),
                    "metadata": {"doc_type": "guideline", "section": section, "topic": ""},
                    "source": filepath,
                    "doc_type": "guideline",
                })

    for para in doc.paragraphs:
        style = para.style.name.lower()
        text = para.text.strip()
        if not text:
            continue
        if style in _HEADING_STYLES or any(style.startswith(h) for h in ("heading", "titolo")):
            flush(current_section, current_text)
            current_section = text
            current_text = ""
        else:
            current_text += " " + text

    flush(current_section, current_text)
    return chunks
