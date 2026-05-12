# Supabase RAG Vector DB — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingest tre documenti (PDF, Excel, DOCX) in un vector database Supabase con ricerca ibrida (vettore + full-text) pronto per alimentare un sistema RAG di generazione schede di allenamento.

**Architecture:** Schema pgvector con tabella `document_chunks` unificata, indici HNSW + GIN, funzione SQL `match_documents()` con Reciprocal Rank Fusion. Pipeline Python: chunker per tipo file → embedder via OpenRouter → upsert Supabase.

**Tech Stack:** Python 3.11+, supabase-py, openai (SDK compat OpenRouter), pymupdf, python-docx, openpyxl, tiktoken, pytest

---

## File Map

```
scripts/
├── requirements.txt
├── schema.sql
├── probe_dim.py           # rileva dim embedding prima di creare lo schema
├── ingest.py              # orchestratore: legge file → chunka → embeds → carica
├── embedder.py            # chiama OpenRouter embedding API
├── uploader.py            # upsert batch su Supabase
├── retriever.py           # search(query, filters, top_k) per il prompt LLM
├── chunkers/
│   ├── __init__.py
│   ├── excel.py
│   ├── docx.py
│   └── pdf.py
└── tests/
    ├── __init__.py
    ├── test_excel.py
    ├── test_docx.py
    ├── test_pdf.py
    ├── test_embedder.py
    ├── test_uploader.py
    └── test_retriever.py
.env                       # root del progetto
```

---

## Task 1: Setup ambiente e .env

**Files:**
- Create: `.env`
- Create: `scripts/requirements.txt`
- Create: `scripts/chunkers/__init__.py`
- Create: `scripts/tests/__init__.py`

- [ ] **Step 1: Crea `.env` nella root del progetto**

```
SUPABASE_URL=<your_supabase_url>
SUPABASE_SERVICE_KEY=<your_supabase_service_role_key>
OPENROUTER_API_KEY=<your_openrouter_api_key>
EMBED_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
```

> Valori reali nel file `.env` locale (non committare mai `.env`).

- [ ] **Step 2: Crea `scripts/requirements.txt`**

```
supabase==2.10.0
openai==1.75.0
pymupdf==1.24.5
python-docx==1.1.2
openpyxl==3.1.5
tiktoken==0.7.0
python-dotenv==1.0.1
pytest==8.2.2
```

- [ ] **Step 3: Installa dipendenze**

```
cd scripts
pip install -r requirements.txt
```

Output atteso: `Successfully installed supabase-... openai-...`

- [ ] **Step 4: Crea file `__init__.py` vuoti**

```
# scripts/chunkers/__init__.py  (vuoto)
# scripts/tests/__init__.py     (vuoto)
```

- [ ] **Step 5: Commit**

```bash
git add .env scripts/requirements.txt scripts/chunkers/__init__.py scripts/tests/__init__.py
git commit -m "chore: setup scripts environment and .env"
```

---

## Task 2: Probe embedding dimension + schema SQL

**Files:**
- Create: `scripts/probe_dim.py`
- Create: `scripts/schema.sql`

- [ ] **Step 1: Crea `scripts/probe_dim.py`**

```python
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

response = client.embeddings.create(
    model=os.getenv("EMBED_MODEL"),
    input=["test dimensione embedding"],
)
dim = len(response.data[0].embedding)
print(f"Embedding dimension: {dim}")
print(f"Usa vector({dim}) nello schema SQL.")
```

- [ ] **Step 2: Esegui probe per scoprire la dimensione reale**

```
cd scripts
python probe_dim.py
```

Output atteso (esempio): `Embedding dimension: 4096`

Nota la dimensione. Se diversa da 4096, aggiorna il valore nel `schema.sql` del passo successivo.

- [ ] **Step 3: Crea `scripts/schema.sql`** (sostituisci `4096` con la dim rilevata se diversa)

```sql
-- Abilita pgvector
create extension if not exists vector;

-- Tabella principale
create table if not exists document_chunks (
  id          uuid primary key default gen_random_uuid(),
  content     text not null,
  embedding   vector(4096),
  fts         tsvector generated always as
                (to_tsvector('italian', content)) stored,
  metadata    jsonb not null default '{}',
  source      text not null,
  doc_type    text not null check (doc_type in ('exercise', 'manual', 'guideline')),
  created_at  timestamptz default now()
);

-- Indice HNSW per ricerca vettoriale (approximate nearest neighbor)
create index if not exists document_chunks_embedding_idx
  on document_chunks using hnsw (embedding vector_cosine_ops);

-- Indice GIN per full-text search italiano
create index if not exists document_chunks_fts_idx
  on document_chunks using gin (fts);

-- Indice GIN per filtri metadata
create index if not exists document_chunks_metadata_idx
  on document_chunks using gin (metadata jsonb_path_ops);

-- Funzione di ricerca ibrida con Reciprocal Rank Fusion
create or replace function match_documents(
  query_embedding  vector(4096),
  query_text       text,
  filter_metadata  jsonb    default '{}',
  match_count      int      default 10,
  vector_weight    float    default 0.7,
  fts_weight       float    default 0.3
)
returns table (
  id         uuid,
  content    text,
  metadata   jsonb,
  doc_type   text,
  source     text,
  similarity float
)
language plpgsql as $$
begin
  return query
  with vector_results as (
    select dc.id,
           1 - (dc.embedding <=> query_embedding) as v_score,
           row_number() over (order by dc.embedding <=> query_embedding) as v_rank
    from document_chunks dc
    where filter_metadata = '{}' or dc.metadata @> filter_metadata
    order by dc.embedding <=> query_embedding
    limit match_count * 3
  ),
  fts_results as (
    select dc.id,
           row_number() over (
             order by ts_rank(dc.fts, plainto_tsquery('italian', query_text)) desc
           ) as f_rank
    from document_chunks dc
    where (filter_metadata = '{}' or dc.metadata @> filter_metadata)
      and dc.fts @@ plainto_tsquery('italian', query_text)
    limit match_count * 3
  ),
  fused as (
    select coalesce(vr.id, fr.id) as id,
           coalesce(1.0 / (60 + vr.v_rank), 0) * vector_weight +
           coalesce(1.0 / (60 + fr.f_rank), 0) * fts_weight  as rrf_score
    from vector_results vr
    full outer join fts_results fr using (id)
  )
  select dc.id, dc.content, dc.metadata, dc.doc_type, dc.source,
         f.rrf_score as similarity
  from fused f
  join document_chunks dc on dc.id = f.id
  order by f.rrf_score desc
  limit match_count;
end; $$;
```

- [ ] **Step 4: Applica lo schema su Supabase**

Apri il Supabase SQL Editor: https://supabase.com/dashboard/project/cmtplysufbgslmpygbfz/sql
Incolla il contenuto di `schema.sql` ed esegui.

Output atteso: nessun errore, tabella `document_chunks` visibile in Table Editor.

- [ ] **Step 5: Commit**

```bash
git add scripts/probe_dim.py scripts/schema.sql
git commit -m "feat: add Supabase pgvector schema with hybrid search function"
```

---

## Task 3: Excel chunker

**Files:**
- Create: `scripts/chunkers/excel.py`
- Test: `scripts/tests/test_excel.py`

- [ ] **Step 1: Scrivi il test**

```python
# scripts/tests/test_excel.py
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
```

- [ ] **Step 2: Esegui il test — deve fallire**

```
cd scripts
pytest tests/test_excel.py -v
```

Output atteso: `ModuleNotFoundError: No module named 'chunkers.excel'`

- [ ] **Step 3: Implementa `scripts/chunkers/excel.py`**

```python
import openpyxl

_MUSCLE_KEYS = {"muscoli", "muscles", "muscle", "gruppi muscolari", "gruppo muscolare"}
_EQUIPMENT_KEYS = {"attrezzatura", "equipment", "attrezzi", "attrezzo"}
_NAME_KEYS = {"nome", "name", "esercizio", "exercise"}
_DIFF_KEYS = {"difficolta", "difficoltà", "difficulty", "livello"}
_CAT_KEYS = {"categoria", "category", "tipologia", "tipo"}


def _find_col(headers_lower: list[str], aliases: set[str]) -> int | None:
    for i, h in enumerate(headers_lower):
        if h in aliases:
            return i
    return None


def _split_list(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in str(value).replace(";", ",").split(",") if v.strip()]


def chunk_excel(filepath: str) -> list[dict]:
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    headers = [str(h).strip() if h else "" for h in rows[0]]
    headers_lower = [h.lower() for h in headers]

    idx_name = _find_col(headers_lower, _NAME_KEYS)
    idx_muscles = _find_col(headers_lower, _MUSCLE_KEYS)
    idx_equipment = _find_col(headers_lower, _EQUIPMENT_KEYS)
    idx_diff = _find_col(headers_lower, _DIFF_KEYS)
    idx_cat = _find_col(headers_lower, _CAT_KEYS)

    chunks = []
    for row in rows[1:]:
        data = dict(zip(headers, row))
        name = str(row[idx_name]).strip() if idx_name is not None and row[idx_name] else ""
        muscles = _split_list(row[idx_muscles]) if idx_muscles is not None else []
        equipment = _split_list(row[idx_equipment]) if idx_equipment is not None else []
        difficulty = str(row[idx_diff]).strip() if idx_diff is not None and row[idx_diff] else ""
        category = str(row[idx_cat]).strip() if idx_cat is not None and row[idx_cat] else ""

        lines = [f"Esercizio: {name}"]
        if muscles:
            lines.append(f"Muscoli: {', '.join(muscles)}")
        if equipment:
            lines.append(f"Attrezzatura: {', '.join(equipment)}")
        if difficulty:
            lines.append(f"Difficoltà: {difficulty}")
        if category:
            lines.append(f"Categoria: {category}")
        # aggiunge campi extra non mappati
        mapped = {idx_name, idx_muscles, idx_equipment, idx_diff, idx_cat}
        for i, (h, v) in enumerate(zip(headers, row)):
            if i not in mapped and v is not None and str(v).strip():
                lines.append(f"{h}: {v}")

        content = "\n".join(lines)
        meta = {
            "doc_type": "exercise",
            "name": name,
            "muscles": muscles,
            "equipment": equipment,
            "difficulty": difficulty,
            "category": category,
        }
        chunks.append({
            "content": content,
            "metadata": meta,
            "source": filepath,
            "doc_type": "exercise",
        })

    return chunks
```

- [ ] **Step 4: Riesegui i test — devono passare**

```
cd scripts
pytest tests/test_excel.py -v
```

Output atteso: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/chunkers/excel.py scripts/tests/test_excel.py
git commit -m "feat: add Excel chunker with structured exercise metadata"
```

---

## Task 4: DOCX chunker

**Files:**
- Create: `scripts/chunkers/docx.py`
- Test: `scripts/tests/test_docx.py`

- [ ] **Step 1: Scrivi il test**

```python
# scripts/tests/test_docx.py
import tempfile, os
from docx import Document as DocxDocument
from docx.oxml.ns import qn
import pytest
from chunkers.docx import chunk_docx


def _make_docx(paragraphs: list[tuple[str, str]]) -> str:
    """paragraphs: list of (style, text). Style: 'Normal' | 'Heading 1' | ..."""
    doc = DocxDocument()
    for style, text in paragraphs:
        p = doc.add_paragraph(text, style=style)
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
```

- [ ] **Step 2: Esegui il test — deve fallire**

```
cd scripts
pytest tests/test_docx.py -v
```

Output atteso: `ModuleNotFoundError: No module named 'chunkers.docx'`

- [ ] **Step 3: Implementa `scripts/chunkers/docx.py`**

```python
import tiktoken
from docx import Document as DocxDocument

_HEADING_STYLES = {"heading 1", "heading 2", "heading 3", "titolo 1", "titolo 2"}
_ENC = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    return len(_ENC.encode(text))


def _split_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
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
```

- [ ] **Step 4: Riesegui i test — devono passare**

```
cd scripts
pytest tests/test_docx.py -v
```

Output atteso: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/chunkers/docx.py scripts/tests/test_docx.py
git commit -m "feat: add DOCX chunker with heading-based section splitting"
```

---

## Task 5: PDF chunker

**Files:**
- Create: `scripts/chunkers/pdf.py`
- Test: `scripts/tests/test_pdf.py`

- [ ] **Step 1: Scrivi il test**

```python
# scripts/tests/test_pdf.py
import tempfile, os
import fitz  # pymupdf
import pytest
from chunkers.pdf import chunk_pdf


def _make_pdf(pages_text: list[str]) -> str:
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 50), text, fontsize=12)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    doc.save(tmp.name)
    doc.close()
    tmp.close()
    return tmp.name


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
```

- [ ] **Step 2: Esegui il test — deve fallire**

```
cd scripts
pytest tests/test_pdf.py -v
```

Output atteso: `ModuleNotFoundError: No module named 'chunkers.pdf'`

- [ ] **Step 3: Implementa `scripts/chunkers/pdf.py`**

```python
import fitz  # pymupdf
import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")


def _split_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
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
    doc = fitz.open(filepath)
    chunks = []

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

    doc.close()
    return chunks
```

- [ ] **Step 4: Riesegui i test — devono passare**

```
cd scripts
pytest tests/test_pdf.py -v
```

Output atteso: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/chunkers/pdf.py scripts/tests/test_pdf.py
git commit -m "feat: add PDF chunker with page tracking and token-based splitting"
```

---

## Task 6: Embedder

**Files:**
- Create: `scripts/embedder.py`
- Test: `scripts/tests/test_embedder.py`

- [ ] **Step 1: Scrivi il test**

```python
# scripts/tests/test_embedder.py
from unittest.mock import MagicMock, patch
import pytest
from embedder import embed_batch, probe_embedding_dim


def _mock_response(dim: int, n: int = 1):
    response = MagicMock()
    response.data = [MagicMock(embedding=[0.1] * dim) for _ in range(n)]
    return response


def test_probe_embedding_dim():
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = _mock_response(dim=4096)
    dim = probe_embedding_dim(mock_client, "test-model")
    assert dim == 4096
    mock_client.embeddings.create.assert_called_once_with(
        model="test-model", input=["probe"]
    )


def test_embed_batch_returns_embeddings():
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = _mock_response(dim=4096, n=3)
    result = embed_batch(mock_client, ["a", "b", "c"], "test-model")
    assert len(result) == 3
    assert len(result[0]) == 4096


def test_embed_batch_splits_into_batches_of_20():
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = [
        _mock_response(dim=4096, n=20),
        _mock_response(dim=4096, n=5),
    ]
    texts = ["t"] * 25
    result = embed_batch(mock_client, texts, "test-model", batch_size=20)
    assert mock_client.embeddings.create.call_count == 2
    assert len(result) == 25


def test_embed_batch_empty_input():
    mock_client = MagicMock()
    result = embed_batch(mock_client, [], "test-model")
    assert result == []
    mock_client.embeddings.create.assert_not_called()
```

- [ ] **Step 2: Esegui il test — deve fallire**

```
cd scripts
pytest tests/test_embedder.py -v
```

Output atteso: `ModuleNotFoundError: No module named 'embedder'`

- [ ] **Step 3: Implementa `scripts/embedder.py`**

```python
from openai import OpenAI


def probe_embedding_dim(client: OpenAI, model: str) -> int:
    response = client.embeddings.create(model=model, input=["probe"])
    return len(response.data[0].embedding)


def embed_batch(
    client: OpenAI,
    texts: list[str],
    model: str,
    batch_size: int = 20,
) -> list[list[float]]:
    if not texts:
        return []
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=model, input=batch)
        embeddings.extend(item.embedding for item in response.data)
    return embeddings
```

- [ ] **Step 4: Riesegui i test — devono passare**

```
cd scripts
pytest tests/test_embedder.py -v
```

Output atteso: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/embedder.py scripts/tests/test_embedder.py
git commit -m "feat: add OpenRouter embedder with batch support and dim probe"
```

---

## Task 7: Uploader

**Files:**
- Create: `scripts/uploader.py`
- Test: `scripts/tests/test_uploader.py`

- [ ] **Step 1: Scrivi il test**

```python
# scripts/tests/test_uploader.py
from unittest.mock import MagicMock, call
import pytest
from uploader import upload_chunks


def _make_chunk(i: int) -> dict:
    return {
        "content": f"contenuto {i}",
        "embedding": [0.1] * 4096,
        "metadata": {"doc_type": "exercise"},
        "source": "test.xlsx",
        "doc_type": "exercise",
    }


def test_upload_chunks_calls_upsert():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    chunks = [_make_chunk(i) for i in range(3)]
    upload_chunks(mock_client, chunks)
    mock_client.table.assert_called_with("document_chunks")
    mock_client.table.return_value.upsert.assert_called_once()


def test_upload_chunks_batch_size():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    chunks = [_make_chunk(i) for i in range(55)]
    upload_chunks(mock_client, chunks, batch_size=20)
    # 55 chunks / 20 = 3 batch calls
    assert mock_client.table.return_value.upsert.call_count == 3


def test_upload_chunks_empty():
    mock_client = MagicMock()
    upload_chunks(mock_client, [])
    mock_client.table.assert_not_called()
```

- [ ] **Step 2: Esegui il test — deve fallire**

```
cd scripts
pytest tests/test_uploader.py -v
```

Output atteso: `ModuleNotFoundError: No module named 'uploader'`

- [ ] **Step 3: Implementa `scripts/uploader.py`**

```python
def upload_chunks(client, chunks: list[dict], batch_size: int = 20) -> None:
    if not chunks:
        return
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        client.table("document_chunks").upsert(batch).execute()
        print(f"  Caricati {min(i + batch_size, len(chunks))}/{len(chunks)} chunk")
```

- [ ] **Step 4: Riesegui i test — devono passare**

```
cd scripts
pytest tests/test_uploader.py -v
```

Output atteso: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/uploader.py scripts/tests/test_uploader.py
git commit -m "feat: add Supabase uploader with batch upsert"
```

---

## Task 8: Retriever

**Files:**
- Create: `scripts/retriever.py`
- Test: `scripts/tests/test_retriever.py`

- [ ] **Step 1: Scrivi il test**

```python
# scripts/tests/test_retriever.py
from unittest.mock import MagicMock
import pytest
from retriever import search


def _mock_supabase(results: list[dict]):
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = results
    return client


def _mock_openai(dim: int = 4096):
    client = MagicMock()
    client.embeddings.create.return_value.data = [MagicMock(embedding=[0.1] * dim)]
    return client


def test_search_returns_results():
    sb = _mock_supabase([{"id": "1", "content": "Panca piana", "similarity": 0.9}])
    oai = _mock_openai()
    results = search(sb, oai, "esercizi petto", model="test-model")
    assert len(results) == 1
    assert results[0]["content"] == "Panca piana"


def test_search_calls_rpc_with_correct_params():
    sb = _mock_supabase([])
    oai = _mock_openai()
    search(sb, oai, "dorsali", model="test-model", filters={"doc_type": "exercise"}, top_k=5)
    sb.rpc.assert_called_once_with(
        "match_documents",
        {
            "query_embedding": [0.1] * 4096,
            "query_text": "dorsali",
            "filter_metadata": {"doc_type": "exercise"},
            "match_count": 5,
        },
    )


def test_search_empty_results():
    sb = _mock_supabase([])
    oai = _mock_openai()
    results = search(sb, oai, "query senza risultati", model="test-model")
    assert results == []
```

- [ ] **Step 2: Esegui il test — deve fallire**

```
cd scripts
pytest tests/test_retriever.py -v
```

Output atteso: `ModuleNotFoundError: No module named 'retriever'`

- [ ] **Step 3: Implementa `scripts/retriever.py`**

```python
def search(
    supabase_client,
    openai_client,
    query: str,
    model: str,
    filters: dict = {},
    top_k: int = 10,
) -> list[dict]:
    response = openai_client.embeddings.create(model=model, input=[query])
    embedding = response.data[0].embedding
    result = supabase_client.rpc(
        "match_documents",
        {
            "query_embedding": embedding,
            "query_text": query,
            "filter_metadata": filters,
            "match_count": top_k,
        },
    ).execute()
    return result.data or []
```

- [ ] **Step 4: Riesegui i test — devono passare**

```
cd scripts
pytest tests/test_retriever.py -v
```

Output atteso: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/retriever.py scripts/tests/test_retriever.py
git commit -m "feat: add retriever with hybrid search via Supabase RPC"
```

---

## Task 9: Orchestratore ingest.py

**Files:**
- Create: `scripts/ingest.py`

- [ ] **Step 1: Crea `scripts/ingest.py`**

```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

from chunkers.excel import chunk_excel
from chunkers.docx import chunk_docx
from chunkers.pdf import chunk_pdf
from embedder import embed_batch, probe_embedding_dim
from uploader import upload_chunks

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
OPENROUTER_KEY = os.environ["OPENROUTER_API_KEY"]
EMBED_MODEL = os.environ["EMBED_MODEL"]

ROOT = Path(__file__).parent.parent
SOURCES = [
    (ROOT / "info.pdf",                  chunk_pdf),
    (ROOT / "set esercizi.xlsx",         chunk_excel),
    (ROOT / "indicazioni schede.docx",   chunk_docx),
]


def main() -> None:
    openai_client = OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("Rilevamento dimensione embedding...")
    dim = probe_embedding_dim(openai_client, EMBED_MODEL)
    print(f"  Dimensione: {dim}")

    for filepath, chunker in SOURCES:
        if not filepath.exists():
            print(f"  SKIP (non trovato): {filepath.name}")
            continue

        print(f"\n→ {filepath.name}")
        chunks = chunker(str(filepath))
        print(f"  Chunk generati: {len(chunks)}")

        texts = [c["content"] for c in chunks]
        print(f"  Embedding in corso (batch da 20)...")
        embeddings = embed_batch(openai_client, texts, EMBED_MODEL)

        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb

        print(f"  Upload su Supabase...")
        upload_chunks(supabase_client, chunks)
        print(f"  Completato: {len(chunks)} chunk caricati")

    print("\nIngestion completata.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Esegui l'ingest completo**

```
cd scripts
python ingest.py
```

Output atteso:
```
Rilevamento dimensione embedding...
  Dimensione: 4096
→ info.pdf
  Chunk generati: 87        (numero indicativo)
  Embedding in corso (batch da 20)...
  Upload su Supabase...
  Completato: 87 chunk caricati
→ set esercizi.xlsx
  ...
→ indicazioni schede.docx
  ...
Ingestion completata.
```

- [ ] **Step 3: Verifica su Supabase**

Vai su: https://supabase.com/dashboard/project/cmtplysufbgslmpygbfz/editor
Esegui:
```sql
select doc_type, source, count(*) from document_chunks group by doc_type, source;
```

Output atteso: righe per `exercise`, `manual`, `guideline` con conteggi > 0.

- [ ] **Step 4: Verifica ricerca ibrida**

Sempre nell'SQL editor:
```sql
-- Questo richiede un embedding reale; verifica che la funzione esiste
select count(*) from document_chunks where doc_type = 'exercise';
select count(*) from document_chunks where doc_type = 'manual';
select count(*) from document_chunks where doc_type = 'guideline';
```

Output atteso: tutti e tre i conteggi > 0.

- [ ] **Step 5: Esegui la suite completa di test**

```
cd scripts
pytest tests/ -v
```

Output atteso: tutti i test passano.

- [ ] **Step 6: Commit**

```bash
git add scripts/ingest.py
git commit -m "feat: add ingestion orchestrator — PDF, Excel, DOCX → Supabase"
```

---

## Task 10: Test end-to-end del retriever da CLI

**Files:**
- Nessun file nuovo — usa `retriever.py` esistente

- [ ] **Step 1: Crea script di smoke test manuale**

```python
# scripts/smoke_test.py  (non committare, solo per verifica locale)
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client
from retriever import search

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
oai = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")

# Test 1: ricerca esercizi per petto
results = search(sb, oai, "esercizi per il petto con bilanciere",
                 model=os.environ["EMBED_MODEL"],
                 filters={"doc_type": "exercise"}, top_k=3)
print("=== Esercizi petto ===")
for r in results:
    print(f"  [{r['similarity']:.4f}] {r['content'][:80]}")

# Test 2: ricerca metodologia
results = search(sb, oai, "come strutturare la progressione di carico",
                 model=os.environ["EMBED_MODEL"], top_k=3)
print("\n=== Metodologia ===")
for r in results:
    print(f"  [{r['similarity']:.4f}] {r['content'][:80]}")
```

- [ ] **Step 2: Esegui il smoke test**

```
cd scripts
python smoke_test.py
```

Output atteso: risultati con similarity > 0 e contenuto rilevante alla query.

- [ ] **Step 3: Commit finale**

```bash
git add scripts/
git commit -m "feat: complete RAG vector DB — ingestion pipeline + hybrid retriever ready"
```

---

## Checklist finale

- [ ] Schema Supabase applicato (tabella + indici + funzione `match_documents`)
- [ ] Tutti e tre i documenti ingeriti (`info.pdf`, `set esercizi.xlsx`, `indicazioni schede.docx`)
- [ ] `pytest tests/ -v` → tutto verde
- [ ] Smoke test → risultati rilevanti su query in italiano
- [ ] `.env` in `.gitignore` (verificare)
