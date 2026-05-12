# Supabase RAG Vector DB — Design Spec
**Date:** 2026-05-12  
**Project:** Prime Training Card Generator  
**Language:** Python

---

## Obiettivo

Costruire un vector database su Supabase (pgvector) che funga da cuore del sistema RAG per la generazione di schede di allenamento personalizzate. Il DB indicizza tre documenti sorgente e risponde a query ibride (semantica + full-text) con filtri strutturati per muscoli, attrezzatura e tipo di contenuto.

---

## Documenti Sorgente

| File | Tipo | Strategia di chunking |
|---|---|---|
| `info.pdf` (5.96 MB) | Manuale di metodologia allenamento | Chunk per sezione ~500 token, overlap 100 token |
| `set esercizi.xlsx` | Database strutturato esercizi | 1 riga Excel = 1 chunk (atomico) |
| `indicazioni schede.docx` | Linee guida per le schede | Chunk per paragrafo/heading ~300 token, overlap 50 token |

---

## Schema Supabase

### Estensione

```sql
create extension if not exists vector;
```

### Tabella `document_chunks`

```sql
create table document_chunks (
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
```

> **Nota:** la dimensione `4096` è basata sull'architettura NVIDIA Nemotron. Se il modello restituisce una dimensione diversa al primo test, la tabella va ricreata con la dimensione corretta prima dell'ingestion completa.

### Indici

```sql
-- Approximate nearest neighbor (HNSW) — più veloce di IVFFlat per <500k righe
create index on document_chunks using hnsw (embedding vector_cosine_ops);

-- Full-text search in italiano
create index on document_chunks using gin (fts);

-- Filtri per metadata (muscles, equipment, doc_type, ecc.)
create index on document_chunks using gin (metadata jsonb_path_ops);
```

### Struttura metadata per `doc_type`

**`exercise`** (da Excel):
```json
{
  "name": "Panca Piana",
  "muscles": ["petto", "tricipiti", "deltoide anteriore"],
  "equipment": ["bilanciere", "panca"],
  "difficulty": "intermedio",
  "category": "forza",
  "sets_range": "3-5",
  "reps_range": "4-8"
}
```

**`manual`** (da PDF):
```json
{
  "section": "Periodizzazione",
  "subsection": "Blocchi di allenamento",
  "topic": "metodologia",
  "page": 12
}
```

**`guideline`** (da DOCX):
```json
{
  "section": "Struttura scheda",
  "topic": "organizzazione",
  "applies_to": ["principianti", "intermedi"]
}
```

---

## Funzione di Ricerca Ibrida

```sql
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
           coalesce(1.0/(60 + vr.v_rank), 0) * vector_weight +
           coalesce(1.0/(60 + fr.f_rank), 0) * fts_weight  as rrf_score
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

**Parametri:**
- `vector_weight` / `fts_weight` — bilanciamento semantica vs keyword (default 70/30)
- `filter_metadata` — pre-filtraggio per muscoli, equipment, doc_type prima della ricerca
- RRF con costante 60: smorza il vantaggio dei top result, robusto a outlier

---

## Architettura Python

```
scripts/
├── ingest.py          # entry point orchestratore
├── chunkers/
│   ├── __init__.py
│   ├── excel.py       # openpyxl → 1 chunk/riga con metadata strutturata
│   ├── docx.py        # python-docx → chunk per heading/paragrafo
│   └── pdf.py         # pymupdf → chunk per sezione con page tracking
├── embedder.py        # OpenRouter embeddings in batch da 20
├── uploader.py        # upsert Supabase con gestione errori e retry
└── retriever.py       # search(query, filters, top_k) → chunks per il prompt
```

### Dipendenze Python

```
supabase
openai
pymupdf
python-docx
openpyxl
tiktoken
python-dotenv
```

### Flusso Ingestion

```
ingest.py
  ├── probe_embedding_dim()   # chiama API con testo test, rileva dim automaticamente
  ├── ensure_schema()         # crea tabella + indici + funzione se non esistono
  └── per ogni file:
        chunker → lista [{"content": str, "metadata": dict, "source": str, "doc_type": str}]
        embedder → aggiunge "embedding": list[float] a ogni chunk
        uploader → batch upsert su Supabase (20 chunk alla volta)
```

### Flusso Query (retriever.py)

```python
def search(query: str, filters: dict = {}, top_k: int = 10) -> list[dict]:
    embedding = embed(query)
    result = supabase.rpc("match_documents", {
        "query_embedding": embedding,
        "query_text": query,
        "filter_metadata": filters,
        "match_count": top_k
    }).execute()
    return result.data
```

---

## Variabili d'ambiente (`.env`)

```
SUPABASE_URL=https://cmtplysufbgslmpygbfz.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
OPENROUTER_API_KEY=<openrouter_key>
EMBED_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
```

---

## Fuori Scope

- Frontend / webapp Next.js (spec separata)
- LLM per generazione schede (già configurato via OpenRouter)
- Autenticazione utenti
- Aggiornamento incrementale dei documenti (re-ingest completo per ora)
