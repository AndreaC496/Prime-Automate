import fitz  # pymupdf
import tiktoken

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


def chunk_pdf(filepath: str, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    chunks = []
    with fitz.open(filepath) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue
            for part in _split_tokens(text, chunk_size, overlap):
                part = part.strip()
                if part:
                    chunks.append({
                        "content": part,
                        "metadata": {
                            "doc_type": "manual",
                            "page": page_num,
                            "section": "",
                            "topic": "",
                        },
                        "source": filepath,
                        "doc_type": "manual",
                    })

    return chunks
