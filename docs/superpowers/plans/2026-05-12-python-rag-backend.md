# Prime Training Python RAG Backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sostituire la logica di generazione TypeScript con un microservizio FastAPI Python che implementa RAG semantico reale (ChromaDB + sentence-transformers) su esercizi (.xlsx) e knowledge base scientifica (.docx + info.pdf), con validazione volume MEV/MAV post-generazione e selezione esercizi probabilistica.

**Architecture:** FastAPI su :8000 espone `/generate`, `/health`, `/ingest`. Next.js route.ts diventa thin proxy. ChromaDB persiste su disco in `backend/db/`. Il retriever usa `paraphrase-multilingual-MiniLM-L12-v2` per embeddings italiani. Selezione esercizi via Stochastic Scored Sampling (SFR + ROM + semantic + priority), garantisce variabilità mantenendo qualità.

**Tech Stack:** Python 3.11+, FastAPI, ChromaDB 0.5+, sentence-transformers 3+, openpyxl, python-docx, PyMuPDF, httpx, pydantic v2, pytest, pytest-anyio

---

## File Map

```
backend/                          ← NUOVO (tutto questo)
├── main.py                       CREATE — FastAPI app, endpoints /generate /health /ingest
├── models.py                     CREATE — Pydantic: UserPreferences, ExerciseEntry, WorkoutDay, WorkoutPlan
├── validator.py                  CREATE — MEV/MAV table, map_muscle, count_sets_by_muscle, validate_volume
├── requirements.txt              CREATE — dipendenze Python
├── .env.example                  CREATE — template variabili ambiente
├── rag/
│   ├── __init__.py               CREATE — empty
│   ├── ingestion.py              CREATE — parse .xlsx/.docx/.pdf → ChromaDB collections
│   ├── retriever.py              CREATE — RAGRetriever, softmax_sample, composite scoring
│   └── prompt.py                 CREATE — build_system_prompt, build_user_prompt + helpers
└── tests/
    ├── __init__.py               CREATE — empty
    ├── test_models.py            CREATE — test Pydantic validation
    ├── test_ingestion.py         CREATE — test estimate_sfr, estimate_rom, normalize_exercise, chunk_text
    ├── test_retriever.py         CREATE — test softmax_sample
    ├── test_validator.py         CREATE — test map_muscle, count_sets_by_muscle, validate_volume
    └── test_main.py              CREATE — test API endpoints con TestClient + mocks

webapp/app/api/generate/route.ts  MODIFY — thin proxy verso :8000 (elimina tutta la logica)
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/rag/__init__.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Crea struttura cartelle**

```powershell
mkdir "C:\Users\andre\Desktop\prime next\backend"
mkdir "C:\Users\andre\Desktop\prime next\backend\rag"
mkdir "C:\Users\andre\Desktop\prime next\backend\tests"
```

- [ ] **Step 2: Crea requirements.txt**

Crea `backend/requirements.txt`:
```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
python-docx>=1.1.0
openpyxl>=3.1.0
pymupdf>=1.24.0
httpx>=0.27.0
pydantic>=2.7.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-anyio>=0.0.0
anyio>=4.0.0
httpx>=0.27.0
```

- [ ] **Step 3: Crea .env.example**

Crea `backend/.env.example`:
```
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b
XLSX_PATH=../set esercizi.xlsx
DOCX_PATH=../indicazioni schede.docx
PDF_PATH=../info.pdf
CHROMA_PATH=db
```

- [ ] **Step 4: Crea file __init__.py**

Crea `backend/rag/__init__.py` (vuoto) e `backend/tests/__init__.py` (vuoto).

- [ ] **Step 5: Crea .env con la tua API key**

Copia `.env.example` in `.env` e inserisci la tua `OPENROUTER_API_KEY`.

```powershell
Copy-Item "C:\Users\andre\Desktop\prime next\backend\.env.example" "C:\Users\andre\Desktop\prime next\backend\.env"
```

Poi modifica `backend/.env` con la chiave reale.

- [ ] **Step 6: Installa dipendenze**

```powershell
cd "C:\Users\andre\Desktop\prime next\backend"
python -m pip install -r requirements.txt
```

Output atteso: `Successfully installed fastapi uvicorn chromadb sentence-transformers ...`

- [ ] **Step 7: Commit**

```powershell
cd "C:\Users\andre\Desktop\prime next"
git init
git add backend/requirements.txt backend/.env.example backend/rag/__init__.py backend/tests/__init__.py
git commit -m "chore: scaffold Python RAG backend structure"
```

---

## Task 2: Pydantic Models

**Files:**
- Create: `backend/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Scrivi il test**

Crea `backend/tests/test_models.py`:
```python
from models import UserPreferences, ExerciseEntry, WorkoutDay, WorkoutPlan


def test_user_preferences_defaults():
    prefs = UserPreferences(
        level="intermedio",
        gender="uomo",
        frequency=4,
        targetMuscles=["petto", "schiena"],
        equipment="palestra",
    )
    assert prefs.notes == ""
    assert prefs.frequency == 4


def test_user_preferences_with_notes():
    prefs = UserPreferences(
        level="avanzato",
        gender="donna",
        frequency=5,
        targetMuscles=["glutei"],
        equipment="home",
        notes="evita squat",
    )
    assert prefs.notes == "evita squat"


def test_exercise_entry_intensity_technique_nullable():
    ex = ExerciseEntry(
        id="d1_e1",
        name="Panca piana con bilanciere",
        primaryMuscle="Pettorali",
        category="Petto",
        sets=3,
        reps="1x5 + 2x8-10",
        rest="3 min",
        notes="scapole retratte",
        intensityTechnique=None,
        equipment="Bilanciere + panca + rack",
    )
    assert ex.intensityTechnique is None


def test_workout_plan_structure():
    prefs = UserPreferences(
        level="intermedio", gender="uomo", frequency=4,
        targetMuscles=["petto"], equipment="palestra",
    )
    ex = ExerciseEntry(
        id="d1_e1", name="Panca piana con bilanciere", primaryMuscle="Pettorali",
        category="Petto", sets=3, reps="8-10", rest="3 min",
        notes="cue", intensityTechnique=None, equipment="Bilanciere",
    )
    day = WorkoutDay(dayNumber=1, name="Upper A", focus="Petto", exercises=[ex])
    plan = WorkoutPlan(
        planName="Piano Test", description="Scheda test",
        userProfile=prefs, days=[day], generatedAt="2026-05-12T00:00:00",
    )
    assert len(plan.days) == 1
    assert plan.days[0].exercises[0].sets == 3
```

- [ ] **Step 2: Verifica che il test fallisca**

```powershell
cd "C:\Users\andre\Desktop\prime next\backend"
python -m pytest tests/test_models.py -v
```

Output atteso: `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Implementa models.py**

Crea `backend/models.py`:
```python
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


class UserPreferences(BaseModel):
    level: str
    gender: str
    frequency: int
    targetMuscles: List[str]
    equipment: str
    notes: Optional[str] = ""


class ExerciseEntry(BaseModel):
    id: str
    name: str
    primaryMuscle: str
    category: str
    sets: int
    reps: str
    rest: str
    notes: str
    intensityTechnique: Optional[str] = None
    equipment: str


class WorkoutDay(BaseModel):
    dayNumber: int
    name: str
    focus: str
    exercises: List[ExerciseEntry]


class WorkoutPlan(BaseModel):
    planName: str
    description: str
    userProfile: UserPreferences
    days: List[WorkoutDay]
    generatedAt: str
```

- [ ] **Step 4: Verifica che i test passino**

```powershell
python -m pytest tests/test_models.py -v
```

Output atteso: `4 passed`

- [ ] **Step 5: Commit**

```powershell
git add backend/models.py backend/tests/test_models.py
git commit -m "feat: add Pydantic models for workout plan schema"
```

---

## Task 3: Ingestion — Pure Functions

**Files:**
- Create: `backend/rag/ingestion.py` (solo pure functions per ora)
- Create: `backend/tests/test_ingestion.py`

- [ ] **Step 1: Scrivi i test**

Crea `backend/tests/test_ingestion.py`:
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.ingestion import (
    estimate_sfr,
    estimate_rom,
    normalize_exercise,
    chunk_text,
)


# ── estimate_sfr ──────────────────────────────────────────────────────────────

def test_sfr_isolation_machine_high():
    score = estimate_sfr("Leg extension", "Macchina leg extension", "Gambe")
    assert score >= 0.85


def test_sfr_barbell_compound_lower():
    score = estimate_sfr("Squat con bilanciere", "Bilanciere + rack", "Gambe")
    assert score <= 0.60


def test_sfr_cable_isolation_medium_high():
    score = estimate_sfr("Pushdown ai cavi", "Macchina cavi", "Braccia")
    assert score >= 0.75


def test_sfr_clamped_between_0_and_1():
    score = estimate_sfr("Esercizio sconosciuto", "Nessuna", "Varie")
    assert 0.0 <= score <= 1.0


# ── estimate_rom ──────────────────────────────────────────────────────────────

def test_rom_overhead_extension_high():
    score = estimate_rom("Estensione tricipiti sopra la testa (Overhead)")
    assert score >= 0.85


def test_rom_incline_curl_high():
    score = estimate_rom("Curl su panca a 45° (Incline curl)")
    assert score >= 0.80


def test_rom_pushdown_low():
    score = estimate_rom("Pushdown ai cavi")
    assert score <= 0.50


def test_rom_squat_high():
    score = estimate_rom("Squat con bilanciere")
    assert score >= 0.75


def test_rom_clamped():
    score = estimate_rom("Esercizio sconosciuto xyz")
    assert 0.0 <= score <= 1.0


# ── normalize_exercise ────────────────────────────────────────────────────────

def test_normalize_standard_columns():
    raw = {
        "name": "Panca piana con bilanciere",
        "primaryMuscle": "Pettorali",
        "secondaryMuscles": "Tricipiti",
        "category": "Petto",
        "equipment": "Bilanciere + panca + rack",
        "homeGym": "si*",
    }
    result = normalize_exercise(raw)
    assert result["name"] == "Panca piana con bilanciere"
    assert result["primaryMuscle"] == "Pettorali"
    assert 0.0 <= result["sfr_score"] <= 1.0
    assert 0.0 <= result["rom_score"] <= 1.0


def test_normalize_italian_columns():
    raw = {
        "nome": "Leg press",
        "muscolo_primario": "Quadricipiti",
        "categoria": "Gambe",
        "attrezzatura": "Macchina leg press",
        "home_gym": "no",
    }
    result = normalize_exercise(raw)
    assert result["name"] == "Leg press"
    assert result["homeGym"] == "no"


def test_normalize_explicit_sfr_rom_columns():
    raw = {
        "name": "Esercizio X",
        "primaryMuscle": "Bicipiti",
        "category": "Braccia",
        "equipment": "Cavi",
        "homeGym": "si",
        "sfr_score": "0.95",
        "rom_score": "0.88",
    }
    result = normalize_exercise(raw)
    assert result["sfr_score"] == 0.95
    assert result["rom_score"] == 0.88


# ── chunk_text ────────────────────────────────────────────────────────────────

def test_chunk_text_single_chunk_short_text():
    text = "Parola " * 100
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) == 1


def test_chunk_text_multiple_chunks():
    text = "Parola " * 700
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) >= 2


def test_chunk_text_overlap_means_words_repeated():
    words = [f"w{i}" for i in range(400)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 2
    last_of_first = chunks[0].split()[-50:]
    first_of_second = chunks[1].split()[:50]
    overlap = set(last_of_first) & set(first_of_second)
    assert len(overlap) > 0


def test_chunk_text_filters_empty():
    chunks = chunk_text("   \n  \n  ", chunk_size=300, overlap=50)
    assert chunks == []
```

- [ ] **Step 2: Verifica che i test falliscano**

```powershell
python -m pytest tests/test_ingestion.py -v
```

Output atteso: `ImportError` o `ModuleNotFoundError`

- [ ] **Step 3: Implementa le pure functions in ingestion.py**

Crea `backend/rag/ingestion.py`:
```python
from __future__ import annotations
import os
from typing import Optional

# ── SFR / ROM scoring ─────────────────────────────────────────────────────────

_ROM_KEYWORDS: dict[str, float] = {
    "overhead": 0.90,
    "sopra la testa": 0.90,
    "incline": 0.85,
    "panca a 45": 0.85,
    "seduto": 0.82,
    "hip thrust": 0.85,
    "romanian": 0.82,
    "rumeno": 0.82,
    "stacco a una gamba": 0.82,
    "pull-up": 0.80,
    "chin-up": 0.80,
    "squat": 0.80,
    "deadlift": 0.80,
    "stacco": 0.78,
    "good morning": 0.78,
    "bulgarian": 0.80,
    "affondi": 0.78,
    "spider curl": 0.78,
    "pushdown": 0.40,
    "alzate laterali": 0.40,
    "kickback": 0.45,
    "face pull": 0.55,
    "peck fly": 0.50,
}


def estimate_rom(name: str) -> float:
    n = name.lower()
    best = 0.55
    for keyword, score in _ROM_KEYWORDS.items():
        if keyword in n:
            best = max(best, score)
    return round(min(1.0, max(0.0, best)), 4)


def estimate_sfr(name: str, equipment: str, category: str) -> float:
    eq = equipment.lower()
    n = name.lower()

    _isolation_words = {"curl", "extension", "fly", "crossover", "kickback", "pushdown", "raise", "alzate", "face pull", "adductor", "abductor", "peck", "leg curl", "leg extension"}
    is_isolation = any(w in n for w in _isolation_words)

    if "macchina" in eq and is_isolation:
        return 0.90
    if ("cavo" in eq or "cavi" in eq) and is_isolation:
        return 0.80
    if "manubr" in eq and is_isolation:
        return 0.75
    if "macchina" in eq:
        return 0.70
    if "bilanciere" in eq:
        return 0.50
    if "nessuna" in eq or "corpo libero" in eq or "corpo-libero" in eq:
        return 0.60
    return 0.60


def normalize_exercise(raw: dict) -> dict:
    def _get(*keys: str) -> str:
        for k in keys:
            v = raw.get(k)
            if v is not None:
                return str(v).strip()
        return ""

    name = _get("name", "nome", "Name", "Esercizio")
    primary = _get("primaryMuscle", "muscolo_primario", "Muscolo Primario", "primary_muscle")
    secondary = _get("secondaryMuscles", "muscoli_secondari", "Muscoli Secondari")
    category = _get("category", "categoria", "Categoria")
    equipment = _get("equipment", "attrezzatura", "Attrezzatura")
    home_gym = _get("homeGym", "home_gym", "Home Gym", "homegym").lower() or "no"

    try:
        sfr = float(raw.get("sfr_score") or raw.get("sfr") or estimate_sfr(name, equipment, category))
    except (TypeError, ValueError):
        sfr = estimate_sfr(name, equipment, category)

    try:
        rom = float(raw.get("rom_score") or raw.get("rom") or estimate_rom(name))
    except (TypeError, ValueError):
        rom = estimate_rom(name)

    return {
        "name": name,
        "primaryMuscle": primary,
        "secondaryMuscles": secondary,
        "category": category,
        "equipment": equipment,
        "homeGym": home_gym,
        "sfr_score": round(min(1.0, max(0.0, sfr)), 4),
        "rom_score": round(min(1.0, max(0.0, rom)), 4),
    }


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


# ── Document extraction ───────────────────────────────────────────────────────

def extract_docx_text(path: str) -> str:
    import docx  # python-docx
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_pdf_text(path: str) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)


def load_exercises_from_xlsx(path: str) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    headers = [str(cell.value).strip() if cell.value else "" for cell in ws[1]]
    exercises: list[dict] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        ex = {headers[i]: val for i, val in enumerate(row) if i < len(headers) and headers[i]}
        exercises.append(ex)
    return exercises


# ── ChromaDB ingestion ────────────────────────────────────────────────────────

def ingest(
    xlsx_path: str,
    docx_path: str,
    pdf_path: str,
    chroma_path: str = "db",
) -> tuple[int, int]:
    import chromadb
    from sentence_transformers import SentenceTransformer

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    model = SentenceTransformer(MODEL_NAME)
    client = chromadb.PersistentClient(path=chroma_path)

    # ── Exercises ──────────────────────────────────────────────────────────────
    try:
        client.delete_collection("exercises")
    except Exception:
        pass
    ex_col = client.create_collection("exercises")

    raw_list = load_exercises_from_xlsx(xlsx_path)
    normalized = [normalize_exercise(r) for r in raw_list if r.get("name") or r.get("nome") or r.get("Name")]

    docs = [
        f"{e['name']} | {e['primaryMuscle']} | {e['category']} | {e['equipment']}"
        for e in normalized
    ]
    embeddings = model.encode(docs, show_progress_bar=True).tolist()
    ids = [f"ex_{i}" for i in range(len(normalized))]
    ex_col.add(documents=docs, embeddings=embeddings, ids=ids, metadatas=normalized)

    # ── Knowledge ──────────────────────────────────────────────────────────────
    try:
        client.delete_collection("knowledge")
    except Exception:
        pass
    kn_col = client.create_collection("knowledge")

    knowledge_text = ""
    if os.path.exists(docx_path):
        knowledge_text += extract_docx_text(docx_path) + "\n"
    if os.path.exists(pdf_path):
        knowledge_text += extract_pdf_text(pdf_path) + "\n"

    chunks = chunk_text(knowledge_text, chunk_size=300, overlap=50)
    kn_embeddings = model.encode(chunks, show_progress_bar=True).tolist()
    kn_ids = [f"kn_{i}" for i in range(len(chunks))]
    kn_metadatas = [{"chunk_index": i} for i in range(len(chunks))]
    kn_col.add(documents=chunks, embeddings=kn_embeddings, ids=kn_ids, metadatas=kn_metadatas)

    return len(normalized), len(chunks)
```

- [ ] **Step 4: Verifica che i test passino**

```powershell
python -m pytest tests/test_ingestion.py -v
```

Output atteso: `14 passed`

- [ ] **Step 5: Commit**

```powershell
git add backend/rag/ingestion.py backend/tests/test_ingestion.py
git commit -m "feat: add ingestion pipeline with SFR/ROM scoring and ChromaDB indexing"
```

---

## Task 4: Prima Ingestione Reale

**Files:**
- Nessun file nuovo — usa `ingestion.ingest()` dalla CLI

- [ ] **Step 1: Esegui l'ingestione reale**

```powershell
cd "C:\Users\andre\Desktop\prime next\backend"
python -c "
from rag.ingestion import ingest
n_ex, n_kn = ingest(
    xlsx_path='../set esercizi.xlsx',
    docx_path='../indicazioni schede.docx',
    pdf_path='../info.pdf',
    chroma_path='db',
)
print(f'Esercizi indicizzati: {n_ex}')
print(f'Knowledge chunks indicizzati: {n_kn}')
"
```

Output atteso (valori dipendono dal contenuto dei file):
```
Esercizi indicizzati: 78+
Knowledge chunks indicizzati: 20+
```

Se `n_ex == 0`: il file .xlsx potrebbe avere intestazioni con nomi diversi. Controlla con:
```powershell
python -c "
import openpyxl
wb = openpyxl.load_workbook('../set esercizi.xlsx')
ws = wb.active
print([str(c.value) for c in ws[1]])
"
```

Aggiusta le chiavi in `normalize_exercise()` nel `_get()` calls se necessario.

- [ ] **Step 2: Verifica ChromaDB**

```powershell
python -c "
import chromadb
c = chromadb.PersistentClient('db')
ex = c.get_collection('exercises')
kn = c.get_collection('knowledge')
print('Exercises:', ex.count())
print('Knowledge chunks:', kn.count())
print('Sample exercise:', ex.peek(1)['metadatas'])
"
```

Output atteso: counts > 0, metadata leggibili.

- [ ] **Step 3: Commit**

```powershell
git add -A
git commit -m "chore: run initial RAG ingestion, ChromaDB populated"
```

---

## Task 5: Retriever — softmax_sample

**Files:**
- Create: `backend/rag/retriever.py` (solo `softmax_sample` per ora)
- Create: `backend/tests/test_retriever.py`

- [ ] **Step 1: Scrivi i test**

Crea `backend/tests/test_retriever.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.retriever import softmax_sample


def test_softmax_sample_returns_correct_count():
    items = [({"name": f"ex{i}"}, float(i)) for i in range(10)]
    result = softmax_sample(items, temperature=0.5, n=5)
    assert len(result) == 5


def test_softmax_sample_no_duplicates():
    items = [({"name": f"ex{i}"}, float(i)) for i in range(10)]
    result = softmax_sample(items, temperature=0.5, n=10)
    names = [r["name"] for r in result]
    assert len(names) == len(set(names))


def test_softmax_sample_low_temp_favors_high_score():
    items = [({"name": "low"}, 0.1), ({"name": "high"}, 10.0)]
    counts = {"low": 0, "high": 0}
    for _ in range(200):
        result = softmax_sample(items, temperature=0.1, n=1)
        counts[result[0]["name"]] += 1
    assert counts["high"] > 180, f"Expected high score to win >180/200 times, got {counts['high']}"


def test_softmax_sample_high_temp_allows_low_score():
    items = [({"name": "low"}, 0.1), ({"name": "high"}, 10.0)]
    counts = {"low": 0, "high": 0}
    for _ in range(200):
        result = softmax_sample(items, temperature=5.0, n=1)
        counts[result[0]["name"]] += 1
    assert counts["low"] > 0, "High temperature should allow low-score items occasionally"


def test_softmax_sample_empty_returns_empty():
    result = softmax_sample([], temperature=0.5, n=5)
    assert result == []


def test_softmax_sample_n_larger_than_pool():
    items = [({"name": f"ex{i}"}, 1.0) for i in range(3)]
    result = softmax_sample(items, temperature=0.5, n=10)
    assert len(result) == 3
```

- [ ] **Step 2: Verifica che i test falliscano**

```powershell
python -m pytest tests/test_retriever.py -v
```

Output atteso: `ImportError`

- [ ] **Step 3: Implementa softmax_sample in retriever.py**

Crea `backend/rag/retriever.py`:
```python
from __future__ import annotations
import math
import random
from typing import Any

from models import UserPreferences


def softmax_sample(
    items: list[tuple[dict, float]],
    temperature: float,
    n: int,
) -> list[dict]:
    """Probabilistic sampling from scored items. Higher score = higher probability.
    temperature controls randomness: low T → deterministic, high T → uniform."""
    if not items:
        return []

    scores = [score for _, score in items]
    max_score = max(scores)
    exp_scores = [math.exp((s - max_score) / temperature) for s in scores]
    total = sum(exp_scores)
    probs = [e / total for e in exp_scores]

    pool = list(range(len(items)))
    pool_probs = probs[:]
    selected: list[dict] = []

    for _ in range(min(n, len(items))):
        total_p = sum(pool_probs)
        if total_p <= 0:
            break
        norm = [p / total_p for p in pool_probs]
        idx = random.choices(pool, weights=norm, k=1)[0]
        pos = pool.index(idx)
        selected.append(items[idx][0])
        pool.pop(pos)
        pool_probs.pop(pos)

    return selected


# ── Compound detection ────────────────────────────────────────────────────────

_COMPOUND_KEYWORDS = {
    "squat", "deadlift", "stacco", "panca", "rematore", "press",
    "pull-up", "chin-up", "dip", "hip thrust", "affondi", "bulgarian",
    "lat machine", "t-bar", "hyperextension", "good morning",
}


def _is_compound(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in _COMPOUND_KEYWORDS)


# ── RAGRetriever ──────────────────────────────────────────────────────────────

class RAGRetriever:
    def __init__(self, chroma_path: str = "db"):
        import chromadb
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self._client = chromadb.PersistentClient(path=chroma_path)
        self.exercises = self._client.get_collection("exercises")
        self.knowledge = self._client.get_collection("knowledge")

    def _build_query(self, prefs: UserPreferences) -> str:
        return (
            f"{prefs.level} {prefs.gender} "
            f"{' '.join(prefs.targetMuscles)} {prefs.equipment} "
            "scheda allenamento ipertrofia evidence-based"
        )

    def get_knowledge_chunks(self, prefs: UserPreferences, n: int = 5) -> list[str]:
        query = self._build_query(prefs)
        embedding = self._model.encode(query).tolist()
        n_results = min(n, self.knowledge.count())
        if n_results == 0:
            return []
        results = self.knowledge.query(
            query_embeddings=[embedding],
            n_results=n_results,
        )
        return results["documents"][0] if results["documents"] else []

    def get_exercises(self, prefs: UserPreferences) -> list[dict]:
        query = self._build_query(prefs)
        embedding = self._model.encode(query).tolist()

        all_count = self.exercises.count()
        if all_count == 0:
            return []

        results = self.exercises.query(
            query_embeddings=[embedding],
            n_results=all_count,
            include=["documents", "metadatas", "distances"],
        )

        compounds: list[tuple[dict, float]] = []
        isolations: list[tuple[dict, float]] = []

        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            home_gym = str(meta.get("homeGym", "no")).lower()

            # Equipment filter
            if prefs.equipment == "home" and home_gym not in ("si", "si*"):
                continue
            if prefs.equipment == "corpo-libero" and home_gym != "si":
                continue

            # Cosine similarity: ChromaDB L2 distance → similarity
            semantic_score = max(0.0, 1.0 - dist / 2.0)

            # Priority bonus
            primary_lower = str(meta.get("primaryMuscle", "")).lower()
            priority_bonus = 0.15 if any(m in primary_lower for m in prefs.targetMuscles) else 0.0

            sfr = float(meta.get("sfr_score", 0.6))
            rom = float(meta.get("rom_score", 0.6))

            composite = sfr * 0.30 + rom * 0.30 + semantic_score * 0.25 + priority_bonus

            entry = (meta, composite)
            if _is_compound(str(meta.get("name", ""))):
                compounds.append(entry)
            else:
                isolations.append(entry)

        selected_compounds = softmax_sample(compounds, temperature=0.35, n=10)
        selected_isolations = softmax_sample(isolations, temperature=0.90, n=10)

        return selected_compounds + selected_isolations
```

- [ ] **Step 4: Verifica che i test passino**

```powershell
python -m pytest tests/test_retriever.py -v
```

Output atteso: `6 passed`

- [ ] **Step 5: Commit**

```powershell
git add backend/rag/retriever.py backend/tests/test_retriever.py
git commit -m "feat: add RAGRetriever with stochastic scored sampling"
```

---

## Task 6: Prompt Builder

**Files:**
- Create: `backend/rag/prompt.py`
- Test inline (nessun file di test separato — le funzioni sono pure string builders, verificate nell'integration test del Task 9)

- [ ] **Step 1: Crea prompt.py**

Crea `backend/rag/prompt.py`:
```python
from __future__ import annotations
from models import UserPreferences

_LEVEL_LABELS = {
    "principiante": "Principiante (0-1 anno)",
    "intermedio": "Intermedio (1-3 anni)",
    "avanzato": "Avanzato (3+ anni)",
}
_EQUIPMENT_LABELS = {
    "palestra": "Palestra completa (tutte le macchine)",
    "home": "Home gym (bilanciere, manubri, panca)",
    "corpo-libero": "Solo corpo libero",
}
_MUSCLE_LABELS = {
    "petto": "Petto", "schiena": "Schiena", "spalle": "Spalle",
    "bicipiti": "Bicipiti", "tricipiti": "Tricipiti",
    "quadricipiti": "Quadricipiti", "femorali": "Femorali", "glutei": "Glutei",
}


def build_system_prompt(knowledge_chunks: list[str]) -> str:
    knowledge_section = ""
    if knowledge_chunks:
        knowledge_section = (
            "\n\n=== LINEE GUIDA CONTESTUALI (dalla knowledge base scientifica) ===\n"
            + "\n---\n".join(knowledge_chunks)
        )

    return (
        "Sei un preparatore atletico certificato con 15 anni di esperienza, "
        "aggiornato con la letteratura scientifica 2015-2025 "
        "(Schoenfeld, Israetel, Maeo, Roberts, Nunes)."
        f"{knowledge_section}\n\n"
        "REGOLE ASSOLUTE - NON violarle mai:\n"
        "1. Rispondi SOLO con JSON valido. Nessun testo prima o dopo.\n"
        "2. USA SOLO esercizi presenti nella lista ESERCIZI DISPONIBILI. "
        'Il campo "name" deve essere copia letterale del nome nella lista.\n'
        "3. MULTI-ARTICOLARI sempre PRIMA degli isolamenti (Nunes et al. 2021).\n"
        "4. Stesso esercizio in 2 giorni: usa SCHEMI DIVERSI "
        "(es. Giorno A 4x5-7 pesante, Giorno B 3x12-15 leggero).\n"
        "5. Esercizi [LOWER_ONLY] (Squat, Deadlift, Leg press, Hip thrust) "
        "SOLO in sessioni Lower/Full Body. Braccia isolate NON in sessioni Lower.\n"
        '6. Ogni "notes" = 1 cue tecnico specifico in italiano. Solo lettere e numeri.\n'
        "7. Rest: 2-3 min per compound, 60-90s per isolamenti.\n"
        "8. Se la lista non ha abbastanza esercizi per un giorno, usa meno — non inventare."
    )


def build_user_prompt(
    prefs: UserPreferences,
    exercises: list[dict],
    knowledge_chunks: list[str],
) -> str:
    level_label = _LEVEL_LABELS.get(prefs.level, prefs.level)
    gender_label = "Donna" if prefs.gender == "donna" else "Uomo"
    muscles_labels = [_MUSCLE_LABELS.get(m, m) for m in prefs.targetMuscles]
    equip_label = _EQUIPMENT_LABELS.get(prefs.equipment, prefs.equipment)

    priority_line = (
        f"- Muscoli prioritari (volume maggiore): {', '.join(muscles_labels)}\n"
        "- Altri muscoli: volume di mantenimento (MEV)"
        if prefs.targetMuscles
        else "- Volume equilibrato su tutti i gruppi"
    )

    exercise_context = _build_exercise_context(exercises)
    volume_targets = _get_volume_targets(prefs.level, prefs.gender)
    level_rules = _get_level_rules(prefs.level)
    split_advice = _get_split_advice(prefs.frequency, prefs.level)
    set_rep_structure = _get_set_rep_structure(prefs.level)
    gender_specific = _get_donna_adaptations() if prefs.gender == "donna" else ""

    return (
        f"Crea una scheda settimanale COMPLETA (allena TUTTI i gruppi muscolari) per:\n"
        f"- Livello: {level_label}\n"
        f"- Sesso: {gender_label}\n"
        f"- Frequenza: {prefs.frequency} sessioni/settimana\n"
        f"{priority_line}\n"
        f"- Attrezzatura: {equip_label}\n"
        f"- Note utente: {prefs.notes or 'nessuna'}\n\n"
        f"{level_rules}\n\n"
        f"VOLUME SETTIMANALE TARGET (serie per gruppo muscolare/settimana):\n"
        f"{volume_targets}\n\n"
        "LINEE GUIDA EVIDENCE-BASED OBBLIGATORIE (letteratura 2021-2025):\n"
        "- TRICIPITI: includi SEMPRE almeno 1 estensione sopra la testa. "
        "Maeo et al. 2023: capo lungo +45% crescita vs pushdown.\n"
        "- BICIPITI: preferire curl in posizione allungata (incline curl, high cable curl). "
        "Alix-Fages, Cyrino: massimizzano ipertrofia capo lungo.\n"
        "- FEMORALI: preferire leg curl seduto > sdraiato. "
        "Maeo et al. 2021: posizione allungata = maggiore ipertrofia.\n"
        "- GLUTEI: Hip thrust OBBLIGATORIO in ogni sessione Lower/Full Body (Plotkin 2023).\n"
        "- SCHIENA: SEMPRE 1 verticale (lat machine, pull-up) + 1 orizzontale (rematore, pulley).\n"
        "- GEMELLI: sia calf in piedi (gastrocnemio) che seduto (soleo) nelle sessioni Lower.\n"
        f"{gender_specific}\n\n"
        "ROTAZIONE ATTREZZI OBBLIGATORIA nella stessa sessione:\n"
        "- Pos 1-2 (compound principali): BILANCIERE\n"
        "- Pos 3-4 (compound accessori): MANUBRI o MACCHINA (non ripetere bilanciere)\n"
        "- Pos 5-6 (isolamento): CAVI o MACCHINE\n\n"
        "FASI SESSIONE:\n"
        "1. FORZA (pos. 1-2): compound bilanciere, top set + back-off, reps 5-10\n"
        "2. IPERTROFIA (pos. 3-4): compound accessori manubri/macchina, reps 8-12\n"
        "3. METABOLICO (pos. 5-6+): isolamenti cavi/macchine, reps 12-20, 1 tecnica intensita'\n\n"
        f"SPLIT CONSIGLIATO PER {prefs.frequency} GIORNI:\n"
        f"{split_advice}\n\n"
        f"ESERCIZI DISPONIBILI (pre-selezionati e ranked per SFR+ROM+rilevanza al tuo profilo):\n"
        f"{exercise_context}\n\n"
        f"{set_rep_structure}\n\n"
        "OUTPUT JSON RICHIESTO:\n"
        "{\n"
        '  "planName": "string",\n'
        '  "description": "string (2 frasi: obiettivo e struttura)",\n'
        '  "days": [\n'
        "    {\n"
        '      "dayNumber": 1,\n'
        '      "name": "Upper A",\n'
        '      "focus": "Petto + Schiena",\n'
        '      "exercises": [\n'
        "        {\n"
        '          "id": "d1_e1",\n'
        '          "name": "NOME ESATTO dalla lista",\n'
        '          "primaryMuscle": "string",\n'
        '          "category": "string",\n'
        '          "sets": 3,\n'
        '          "reps": "8-10",\n'
        '          "rest": "90s",\n'
        '          "notes": "cue tecnico specifico",\n'
        '          "intensityTechnique": null,\n'
        '          "equipment": "string"\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Genera ESATTAMENTE {prefs.frequency} giorni. "
        "6-8 esercizi per giorno. La scheda deve essere scientificamente fondata, varia e progressiva."
    )


def _build_exercise_context(exercises: list[dict]) -> str:
    lines: list[str] = []
    compounds = [e for e in exercises if _is_compound_meta(e)]
    isolations = [e for e in exercises if not _is_compound_meta(e)]

    if compounds:
        lines.append("=== MULTI-ARTICOLARI (mettili PRIMA nella sessione) ===")
        for e in compounds:
            lines.append(_fmt_exercise(e))

    if isolations:
        lines.append("\n=== MONO-ARTICOLARI / ISOLAMENTO ===")
        for e in isolations:
            lines.append(_fmt_exercise(e))

    return "\n".join(lines)


def _is_compound_meta(e: dict) -> bool:
    _COMPOUND_KEYWORDS = {
        "squat", "deadlift", "stacco", "panca", "rematore", "press",
        "pull-up", "chin-up", "dip", "hip thrust", "affondi", "bulgarian",
        "lat machine", "t-bar", "hyperextension", "good morning",
    }
    n = str(e.get("name", "")).lower()
    return any(k in n for k in _COMPOUND_KEYWORDS)


def _fmt_exercise(e: dict) -> str:
    name = e.get("name", "")
    primary = e.get("primaryMuscle", "")
    equipment = e.get("equipment", "")
    sfr = e.get("sfr_score", 0.6)
    rom = e.get("rom_score", 0.6)
    return f"  {name} | {primary} | {equipment} | SFR:{sfr:.1f} ROM:{rom:.1f}"


def _get_volume_targets(level: str, gender: str) -> str:
    is_donna = gender == "donna"
    lv = level.lower()
    if "avanzato" in lv:
        glutei = "14-16" if is_donna else "10-14"
        return (
            f"Petto: 16-20 set | Schiena: 18-22 set | Trapezi: 12-16 set\n"
            f"Spalle: 16-22 set | Bicipiti: 14-20 set | Tricipiti: 12-14 set\n"
            f"Quadricipiti: 14-18 set | Femorali: 12-16 set | Glutei: {glutei} set | Gemelli: 14-16 set"
        )
    if "intermedio" in lv:
        glutei = "10-14" if is_donna else "6-10"
        return (
            f"Petto: 12-16 set | Schiena: 14-18 set | Trapezi: 10-14 set\n"
            f"Spalle: 12-16 set | Bicipiti: 12-14 set | Tricipiti: 10-12 set\n"
            f"Quadricipiti: 12-14 set | Femorali: 10-12 set | Glutei: {glutei} set | Gemelli: 12-14 set"
        )
    glutei = "8-12" if is_donna else "4-8"
    return (
        f"Petto: 6-10 set | Schiena: 8-12 set | Trapezi: 6-8 set\n"
        f"Spalle: 8-12 set | Bicipiti: 6-8 set | Tricipiti: 6-8 set\n"
        f"Quadricipiti: 8-10 set | Femorali: 6-8 set | Glutei: {glutei} set | Gemelli: 8-10 set"
    )


def _get_donna_adaptations() -> str:
    return (
        "\nADATTAMENTI PER DONNA (Roberts et al. 2020, Hunter 2014):\n"
        "- Treno inferiore: volume MAGGIORE (glutei e quadricipiti priorita' fisiologica)\n"
        "- Recupero inter-serie: 90s per multi-articolari, 45-60s per isolamenti\n"
        "- Glutei: Hip thrust + Glute kickback o Abductor machine in ogni sessione Lower\n"
        "- Petto/tricipiti: volume RIDOTTO di 2-3 set rispetto all'uomo\n"
        "- Esercizi unilaterali gambe preferiti (affondi, Bulgarian split squat)"
    )


def _get_set_rep_structure(level: str) -> str:
    lv = level.lower()
    if "principiante" in lv:
        return (
            "STRUTTURA SET/REP — PRINCIPIANTE (3-4 set, top set incluso):\n"
            "A) COMPOUND bilanciere (pos.1-2): TOP SET + BACK-OFF, 3-4 sets\n"
            '   Es: "sets":3,"reps":"1x8 + 2x10-12". Top set RPE 7-8. Rest: 3 min.\n'
            "B) COMPOUND accessori manubri/macchina (pos.3-4): 3 set\n"
            '   Es: "sets":3,"reps":"10-12". Rest: 2 min.\n'
            "C) ISOLAMENTI cavi/macchine (pos.5+): 3 set\n"
            '   Es: "sets":3,"reps":"12-15". Rest: 60-90s.'
        )
    if "intermedio" in lv:
        return (
            "STRUTTURA SET/REP — INTERMEDIO (3 set, top set incluso):\n"
            "A) COMPOUND bilanciere (pos.1-2): TOP SET + BACK-OFF, 3 sets\n"
            '   Es: "sets":3,"reps":"1x5 + 2x8-10". Top set RPE 8-9. Rest: 3-4 min.\n'
            "B) COMPOUND accessori manubri/macchina (pos.3-4): 3 set\n"
            '   Es: "sets":3,"reps":"8-12". Rest: 90s-2 min.\n'
            "C) ISOLAMENTI (pos.5+): 3 set, 1 tecnica intensita' sull\'ultimo\n"
            '   Es: "sets":3,"reps":"12-15". Rest: 60-90s.'
        )
    return (
        "!!!! STRUTTURA SET/REP — AVANZATO — REGOLA CRITICA !!!!\n"
        "DEFAULT OBBLIGATORIO: 2 set per esercizio. NON usare 3 set come default.\n"
        "A) COMPOUND bilanciere: TOP SET + BACK-OFF, 2 set\n"
        '   DEFAULT: "sets":2,"reps":"1x3 + 1x5-7". Top set RPE 9-10. Rest: 4-5 min.\n'
        "B) COMPOUND accessori manubri/macchina: 2 set\n"
        '   "sets":2,"reps":"6-10". Rest: 2-3 min.\n'
        "C) ISOLAMENTI (pos.5+): 2 set\n"
        '   "sets":2,"reps":"10-15". Rest: 60-90s.\n'
        "VERIFICA FINALE: la maggioranza degli esercizi DEVE avere sets:2."
    )


def _get_level_rules(level: str) -> str:
    lv = level.lower()
    if "principiante" in lv:
        return (
            "REGOLE LIVELLO PRINCIPIANTE:\n"
            "- Top set: RPE 7-8 (tecnica prioritaria, non massimizzare carico)\n"
            "- Rep range compound: 8-12\n"
            "- Rep range isolamento: 12-15\n"
            "- NO tecniche avanzate di intensita' (drop set, myo-reps)\n"
            "- RIR 2-3 su tutti gli esercizi"
        )
    if "intermedio" in lv:
        return (
            "REGOLE LIVELLO INTERMEDIO:\n"
            "- Top set: RPE 8-9, compound principali 5-8 rep, accessori 8-12 rep\n"
            "- Rep range isolamento: 10-15\n"
            "- 1 tecnica intensita' per sessione, solo sull'ultimo isolamento\n"
            "- RIR 1-2 sui compound, RIR 0-1 sugli isolamenti"
        )
    return (
        "REGOLE LIVELLO AVANZATO:\n"
        "- Top set: RPE 9-10, compound principali 3-6 rep (forza massimale)\n"
        "- Back-off: 5-8 rep, RPE 8, intensita' 80-85%\n"
        "- Rep range compound accessori: 6-10 rep\n"
        "- Rep range isolamento: 10-15, near-failure\n"
        "- 1-2 tecniche intensita' per sessione\n"
        "- RIR 0-1 su tutti gli esercizi"
    )


def _get_split_advice(frequency: int, level: str) -> str:
    is_principiante = "principiante" in level.lower()

    splits: dict[int, str] = {
        2: (
            "Full Body A + Full Body B (ogni gruppo 2x/settimana)\n"
            "  - Giorno A (Squat-dominant): Squat + Panca piana + Rematore + Hip thrust + Alzate laterali + Curl + Polpacci\n"
            "  - Giorno B (Hinge-dominant): Stacco rumeno + Military press + Lat machine + Leg press + Croci + Pushdown + Polpacci"
        ),
        3: (
            "Full Body A / Full Body B / Full Body C\n"
            "  - Giorno A: Squat + Panca piana + Rematore + Hip thrust + Alzate laterali + Curl manubri + Polpacci\n"
            "  - Giorno B: Stacco rumeno + Military press + Lat machine + Leg press + Cable crossover + Pushdown + Polpacci\n"
            "  - Giorno C: Bulgarian split squat + Panca inclinata + Pulley + Leg extension + Reverse fly + Hammer curl + Calf seduto"
            if is_principiante else
            "Lower / Upper / Full Body (ogni gruppo 2x/settimana)\n"
            "  - Lower: Squat + Hip thrust + Stacco rumeno + Leg curl seduto + Leg extension + Polpacci x2\n"
            "  - Upper: Panca piana + Rematore + Panca inclinata + Lat machine + Alzate laterali + Overhead ext. + Curl\n"
            "  - Full Body: 3-4 esercizi lower hinge-dominant + 2-3 upper varianti diverse da Upper"
        ),
        4: (
            "Upper A / Lower A / Upper B / Lower B (split ottimale per ipertrofia, Schoenfeld 2019)\n"
            "  - Upper A: Panca bil. + Rematore bil. + Panca inclinata manubri + Lat machine + Alzate laterali cavi + Overhead ext.\n"
            "  - Lower A (quad-dom): Squat bil. + Hip thrust bil. + Leg press + Leg curl seduto + Calf piedi + Calf seduto\n"
            "  - Upper B: Rematore manubrio + Panca piana manubri + Pulley cavi + Chest press macchina + Incline curl + Pushdown\n"
            "  - Lower B (hinge-dom): RDL bil. + Bulgarian split squat + Leg extension + Glute kickback cavi + Single-leg RDL + Calf seduto"
        ),
        5: (
            "Push / Pull / Legs / Upper / Lower (PPLUL - ogni gruppo 2x/settimana)\n"
            "  - Push: panca bilanciere + military + panca inclinata + alzate laterali + overhead extension + pushdown\n"
            "  - Pull: stacco + lat machine + rematore + face pull + incline curl + hammer curl\n"
            "  - Legs: squat + hip thrust + RDL + leg curl seduto + leg extension + polpacci x2\n"
            "  - Upper (accessorio): varianti petto/schiena diverse + braccia\n"
            "  - Lower (accessorio): hinge-dominant + glutei + polpacci"
        ),
        6: (
            "Push / Pull / Legs x 2 (ogni muscolo 2x/settimana)\n"
            "  - Push A: panca bilanciere, military press, panca inclinata manubri, alzate laterali, overhead ext., pushdown\n"
            "  - Pull A: stacco, lat machine, rematore bilanciere, face pull, incline curl, hammer curl\n"
            "  - Legs A: squat, hip thrust, RDL, leg curl seduto, leg extension, calf piedi\n"
            "  - Push B: panca manubri, shoulder press macchina, alzate laterali cavi, croci, kickback (SCHEMA DIVERSO da Push A)\n"
            "  - Pull B: stacco rumeno, pull-up, rematore manubrio, pulley, curl EZ, curl cavi alti\n"
            "  - Legs B: hack squat/leg press, hip thrust (SCHEMA DIVERSO), Bulgarian split, adductor/abductor, leg curl seduto, calf seduto"
        ),
    }
    return splits.get(frequency, f"{frequency} sessioni — split Upper/Lower o PPL appropriato")
```

- [ ] **Step 2: Quick smoke test**

```powershell
python -c "
from rag.prompt import build_system_prompt, build_user_prompt
from models import UserPreferences
prefs = UserPreferences(level='intermedio', gender='uomo', frequency=4, targetMuscles=['petto'], equipment='palestra')
sp = build_system_prompt(['chunk di test'])
up = build_user_prompt(prefs, [{'name': 'Panca piana con bilanciere', 'primaryMuscle': 'Pettorali', 'category': 'Petto', 'equipment': 'Bilanciere', 'sfr_score': 0.5, 'rom_score': 0.7}], [])
print('System prompt OK, len:', len(sp))
print('User prompt OK, len:', len(up))
assert 'LINEE GUIDA CONTESTUALI' in sp
assert 'Panca piana' in up
print('PASS')
"
```

Output atteso: `PASS`

- [ ] **Step 3: Commit**

```powershell
git add backend/rag/prompt.py
git commit -m "feat: add prompt builder with knowledge chunk injection and full evidence-based rules"
```

---

## Task 7: Volume Validator

**Files:**
- Create: `backend/validator.py`
- Create: `backend/tests/test_validator.py`

- [ ] **Step 1: Scrivi i test**

Crea `backend/tests/test_validator.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import UserPreferences, ExerciseEntry, WorkoutDay, WorkoutPlan
from validator import map_muscle, count_sets_by_muscle, validate_volume, build_retry_hint


def _make_prefs(level="intermedio", muscles=None):
    return UserPreferences(
        level=level, gender="uomo", frequency=4,
        targetMuscles=muscles or ["petto"],
        equipment="palestra",
    )


def _make_exercise(primary: str, sets: int) -> ExerciseEntry:
    return ExerciseEntry(
        id="test", name="Esercizio Test", primaryMuscle=primary,
        category="Test", sets=sets, reps="8-10", rest="90s",
        notes="cue", intensityTechnique=None, equipment="Bilanciere",
    )


def _make_plan(exercises_by_primary: list[tuple[str, int]], prefs: UserPreferences) -> WorkoutPlan:
    exercises = [_make_exercise(p, s) for p, s in exercises_by_primary]
    day = WorkoutDay(dayNumber=1, name="Test", focus="Test", exercises=exercises)
    return WorkoutPlan(
        planName="Test", description="Test", userProfile=prefs,
        days=[day], generatedAt="2026-05-12T00:00:00",
    )


# ── map_muscle ────────────────────────────────────────────────────────────────

def test_map_pettorali_to_petto():
    assert map_muscle("Pettorali") == "petto"


def test_map_gran_dorsale_to_schiena():
    assert map_muscle("Gran dorsale, Romboidei") == "schiena"


def test_map_deltoidi_to_spalle():
    assert map_muscle("Deltoidi laterali") == "spalle"


def test_map_bicipiti():
    assert map_muscle("Bicipiti (capo lungo)") == "bicipiti"


def test_map_tricipiti():
    assert map_muscle("Tricipiti (capo lungo)") == "tricipiti"


def test_map_quadricipiti():
    assert map_muscle("Quadricipiti") == "quadricipiti"


def test_map_femorali():
    assert map_muscle("Femorali, Glutei") == "femorali"


def test_map_glutei():
    assert map_muscle("Glutei") == "glutei"


def test_map_unknown_returns_none():
    assert map_muscle("Core, Trasverso addome") is None


# ── count_sets_by_muscle ──────────────────────────────────────────────────────

def test_count_sets_aggregates_same_muscle():
    prefs = _make_prefs()
    plan = _make_plan([("Pettorali", 3), ("Pettorali", 3), ("Pettorali", 3)], prefs)
    counts = count_sets_by_muscle(plan)
    assert counts["petto"] == 9


def test_count_sets_multiple_muscles():
    prefs = _make_prefs()
    plan = _make_plan([("Pettorali", 3), ("Gran dorsale", 3)], prefs)
    counts = count_sets_by_muscle(plan)
    assert counts["petto"] == 3
    assert counts["schiena"] == 3


def test_count_sets_ignores_unknown_muscles():
    prefs = _make_prefs()
    plan = _make_plan([("Core", 3)], prefs)
    counts = count_sets_by_muscle(plan)
    assert "petto" not in counts


# ── validate_volume ───────────────────────────────────────────────────────────

def test_validate_priority_muscle_below_mev_is_critical():
    prefs = _make_prefs(level="intermedio", muscles=["petto"])
    # petto MEV intermedio = 12. Mettiamo solo 6 set.
    plan = _make_plan([("Pettorali", 3), ("Pettorali", 3)], prefs)
    critical, warnings = validate_volume(plan, prefs)
    assert any("petto" in c for c in critical)


def test_validate_non_priority_below_mev_is_warning_only():
    prefs = _make_prefs(level="intermedio", muscles=["schiena"])
    # petto non è priorità, è sotto MEV → warning
    plan = _make_plan([("Gran dorsale", 15)], prefs)
    critical, warnings = validate_volume(plan, prefs)
    assert not any("schiena" in c for c in critical)  # schiena ha 15 set, ok


def test_validate_over_mav_is_warning():
    prefs = _make_prefs(level="intermedio", muscles=["petto"])
    # petto MAV intermedio = 16. Mettiamo 20 set.
    plan = _make_plan([("Pettorali", 5)] * 4, prefs)
    _, warnings = validate_volume(plan, prefs)
    assert any("petto" in w for w in warnings)


def test_validate_within_range_no_violations():
    prefs = _make_prefs(level="intermedio", muscles=["petto"])
    # petto MEV=12 MAV=16. Mettiamo 14 set.
    exercises = [("Pettorali", 3)] * 4 + [("Gran dorsale", 4)] * 4
    plan = _make_plan(exercises, prefs)
    critical, warnings = validate_volume(plan, prefs)
    petto_critical = [c for c in critical if "petto" in c]
    petto_warnings = [w for w in warnings if "petto" in w]
    assert len(petto_critical) == 0
    assert len(petto_warnings) == 0


# ── build_retry_hint ──────────────────────────────────────────────────────────

def test_retry_hint_contains_violations():
    hint = build_retry_hint(["petto: 6 set < MEV (12)", "glutei: 4 set < MEV (6)"])
    assert "petto" in hint
    assert "glutei" in hint
    assert "MEV" in hint
```

- [ ] **Step 2: Verifica che i test falliscano**

```powershell
python -m pytest tests/test_validator.py -v
```

Output atteso: `ImportError`

- [ ] **Step 3: Implementa validator.py**

Crea `backend/validator.py`:
```python
from __future__ import annotations
from models import UserPreferences, WorkoutPlan

MEV_MAV: dict[str, dict[str, tuple[int, int]]] = {
    "principiante": {
        "petto": (6, 10), "schiena": (8, 12), "spalle": (8, 12),
        "bicipiti": (6, 8), "tricipiti": (6, 8),
        "quadricipiti": (8, 10), "femorali": (6, 8), "glutei": (4, 8),
    },
    "intermedio": {
        "petto": (12, 16), "schiena": (14, 18), "spalle": (12, 16),
        "bicipiti": (12, 14), "tricipiti": (10, 12),
        "quadricipiti": (12, 14), "femorali": (10, 12), "glutei": (6, 10),
    },
    "avanzato": {
        "petto": (16, 20), "schiena": (18, 22), "spalle": (16, 22),
        "bicipiti": (14, 20), "tricipiti": (12, 14),
        "quadricipiti": (14, 18), "femorali": (12, 16), "glutei": (10, 14),
    },
}

_MUSCLE_MAP: dict[str, str] = {
    "pettorali": "petto", "petto": "petto",
    "gran dorsale": "schiena", "dorsale": "schiena", "schiena": "schiena",
    "romboidei": "schiena", "trapezio": "schiena",
    "deltoidi": "spalle", "deltoide": "spalle", "spalle": "spalle",
    "bicipiti": "bicipiti", "bicipite": "bicipiti",
    "tricipiti": "tricipiti", "tricipite": "tricipiti",
    "quadricipiti": "quadricipiti", "quadricipite": "quadricipiti",
    "femorali": "femorali", "femorale": "femorali", "bicipite femorale": "femorali",
    "glutei": "glutei", "gluteo": "glutei",
}


def map_muscle(primary_muscle: str) -> str | None:
    lower = primary_muscle.lower()
    for key, val in _MUSCLE_MAP.items():
        if key in lower:
            return val
    return None


def count_sets_by_muscle(plan: WorkoutPlan) -> dict[str, int]:
    counts: dict[str, int] = {}
    for day in plan.days:
        for ex in day.exercises:
            muscle = map_muscle(ex.primaryMuscle)
            if muscle:
                counts[muscle] = counts.get(muscle, 0) + ex.sets
    return counts


def validate_volume(
    plan: WorkoutPlan,
    prefs: UserPreferences,
) -> tuple[list[str], list[str]]:
    mev_mav = MEV_MAV.get(prefs.level, MEV_MAV["intermedio"])
    counts = count_sets_by_muscle(plan)
    critical: list[str] = []
    warnings: list[str] = []

    for muscle, (mev, mav) in mev_mav.items():
        total = counts.get(muscle, 0)
        is_priority = muscle in prefs.targetMuscles
        if total < mev:
            msg = f"{muscle}: {total} set < MEV ({mev})"
            (critical if is_priority else warnings).append(msg)
        elif total > mav:
            warnings.append(f"{muscle}: {total} set > MAV ({mav})")

    return critical, warnings


def build_retry_hint(critical_violations: list[str]) -> str:
    items = "\n".join(f"- {v}" for v in critical_violations)
    return (
        "ATTENZIONE: Il piano precedente aveva questi problemi di volume:\n"
        f"{items}\n"
        "Correggi aggiungendo set per i muscoli sotto MEV prima di rispondere."
    )
```

- [ ] **Step 4: Verifica che i test passino**

```powershell
python -m pytest tests/test_validator.py -v
```

Output atteso: `18 passed`

- [ ] **Step 5: Commit**

```powershell
git add backend/validator.py backend/tests/test_validator.py
git commit -m "feat: add volume validator with MEV/MAV/MRV enforcement"
```

---

## Task 8: FastAPI App

**Files:**
- Create: `backend/main.py`
- Create: `backend/tests/test_main.py`

- [ ] **Step 1: Scrivi i test**

Crea `backend/tests/test_main.py`:
```python
import sys, os, json
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

# Mock del retriever PRIMA di importare main
mock_retriever = MagicMock()
mock_retriever.exercises.count.return_value = 42
mock_retriever.knowledge.count.return_value = 15
mock_retriever.get_knowledge_chunks.return_value = ["chunk scientifico di test"]
mock_retriever.get_exercises.return_value = [
    {
        "name": "Panca piana con bilanciere", "primaryMuscle": "Pettorali",
        "category": "Petto", "equipment": "Bilanciere + panca + rack",
        "homeGym": "si*", "sfr_score": 0.5, "rom_score": 0.7,
    }
]

SAMPLE_PLAN_JSON = json.dumps({
    "planName": "Piano Test",
    "description": "Scheda di test per validazione.",
    "days": [
        {
            "dayNumber": 1, "name": "Upper A", "focus": "Petto + Schiena",
            "exercises": [
                {
                    "id": "d1_e1", "name": "Panca piana con bilanciere",
                    "primaryMuscle": "Pettorali", "category": "Petto",
                    "sets": 3, "reps": "1x5 + 2x8-10", "rest": "3 min",
                    "notes": "scapole retratte", "intensityTechnique": None,
                    "equipment": "Bilanciere + panca + rack",
                }
            ],
        }
    ],
})

VALID_PAYLOAD = {
    "level": "intermedio",
    "gender": "uomo",
    "frequency": 4,
    "targetMuscles": ["petto"],
    "equipment": "palestra",
    "notes": "",
}


def _make_client():
    import main
    # Set mock BEFORE TestClient so startup guard (if retriever is not None: return) skips re-init
    main.retriever = mock_retriever
    return TestClient(main.app)


def test_health_returns_ok():
    client = _make_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db_loaded"] is True
    assert data["exercises_count"] == 42


def test_generate_returns_workout_plan():
    # call_llm is async — must use AsyncMock
    with patch("main.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = SAMPLE_PLAN_JSON
        client = _make_client()
        resp = client.post("/generate", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["planName"] == "Piano Test"
    assert len(data["days"]) == 1
    assert "_meta" in data


def test_generate_meta_contains_generation_info():
    with patch("main.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = SAMPLE_PLAN_JSON
        client = _make_client()
        resp = client.post("/generate", json=VALID_PAYLOAD)
    meta = resp.json()["_meta"]
    assert "generation_ms" in meta
    assert "exercises_retrieved" in meta
    assert "knowledge_chunks_used" in meta
    assert isinstance(meta["warnings"], list)


def test_generate_503_when_retriever_none():
    import main
    original = main.retriever
    main.retriever = None
    client = TestClient(main.app)
    resp = client.post("/generate", json=VALID_PAYLOAD)
    assert resp.status_code == 503
    main.retriever = original


def test_generate_missing_field_422():
    client = _make_client()
    resp = client.post("/generate", json={"level": "intermedio"})
    assert resp.status_code == 422


def test_extract_json_handles_markdown_fences():
    from main import extract_json
    raw = "```json\n" + SAMPLE_PLAN_JSON + "\n```"
    result = extract_json(raw)
    parsed = json.loads(result)
    assert parsed["planName"] == "Piano Test"


def test_extract_json_handles_clean_json():
    from main import extract_json
    result = extract_json(SAMPLE_PLAN_JSON)
    parsed = json.loads(result)
    assert "days" in parsed
```

- [ ] **Step 2: Verifica che i test falliscano**

```powershell
python -m pytest tests/test_main.py -v
```

Output atteso: `ImportError: No module named 'main'`

- [ ] **Step 3: Implementa main.py**

Crea `backend/main.py`:
```python
from __future__ import annotations
import json
import os
import re
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import UserPreferences, WorkoutPlan, WorkoutDay, ExerciseEntry
from rag.ingestion import ingest
from rag.retriever import RAGRetriever
from rag.prompt import build_system_prompt, build_user_prompt
from validator import validate_volume, build_retry_hint

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b")
XLSX_PATH = os.getenv("XLSX_PATH", "../set esercizi.xlsx")
DOCX_PATH = os.getenv("DOCX_PATH", "../indicazioni schede.docx")
PDF_PATH = os.getenv("PDF_PATH", "../info.pdf")
CHROMA_PATH = os.getenv("CHROMA_PATH", "db")

app = FastAPI(title="Prime Training RAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

retriever: RAGRetriever | None = None


@app.on_event("startup")
async def startup() -> None:
    global retriever
    if retriever is not None:  # allows tests to inject a mock before TestClient creation
        return
    try:
        retriever = RAGRetriever(chroma_path=CHROMA_PATH)
    except Exception as e:
        print(f"[startup] ChromaDB not ready: {e}. Call POST /ingest first.")
        retriever = None


# ── JSON extraction ────────────────────────────────────────────────────────────

def extract_json(raw: str) -> str:
    trimmed = raw.strip()
    try:
        json.loads(trimmed)
        return trimmed
    except json.JSONDecodeError:
        pass

    stripped = re.sub(r"^```(?:json)?\n?", "", trimmed)
    stripped = re.sub(r"\n?```$", "", stripped).strip()
    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response")

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]

    return raw[start:]


# ── LLM call ──────────────────────────────────────────────────────────────────

async def call_llm(system_prompt: str, user_prompt: str, extra_hint: str = "") -> str:
    full_user = (extra_hint + "\n\n" + user_prompt) if extra_hint else user_prompt
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://prime-training.app",
                "X-Title": "Prime Training Card Generator",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_user},
                ],
                "temperature": 0.3,
                "max_tokens": 10000,
                "reasoning": {"enabled": False},
            },
        )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    if not content:
        raise ValueError("Empty response from model")
    return content


# ── Plan parsing ──────────────────────────────────────────────────────────────

def parse_plan(raw: str, prefs: UserPreferences) -> WorkoutPlan:
    json_str = extract_json(raw)
    parsed = json.loads(json_str)

    days: list[WorkoutDay] = []
    for i, day in enumerate(parsed.get("days", [])):
        exercises: list[ExerciseEntry] = []
        for j, ex in enumerate(day.get("exercises", [])):
            exercises.append(
                ExerciseEntry(
                    id=str(ex.get("id", f"d{i+1}_e{j+1}")),
                    name=str(ex.get("name", "")),
                    primaryMuscle=str(ex.get("primaryMuscle", "")),
                    category=str(ex.get("category", "")),
                    sets=int(ex.get("sets", 3)),
                    reps=str(ex.get("reps", "8-10")),
                    rest=str(ex.get("rest", "90s")),
                    notes=str(ex.get("notes", "")),
                    intensityTechnique=ex.get("intensityTechnique"),
                    equipment=str(ex.get("equipment", "")),
                )
            )
        days.append(
            WorkoutDay(
                dayNumber=int(day.get("dayNumber", i + 1)),
                name=str(day.get("name", f"Giorno {i + 1}")),
                focus=str(day.get("focus", "")),
                exercises=exercises,
            )
        )

    return WorkoutPlan(
        planName=str(parsed.get("planName", "Piano di Allenamento")),
        description=str(parsed.get("description", "")),
        userProfile=prefs,
        days=days,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/generate")
async def generate(prefs: UserPreferences) -> dict:
    if retriever is None:
        raise HTTPException(status_code=503, detail="RAG not initialized. Call POST /ingest first.")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured.")

    t0 = time.time()

    knowledge_chunks = retriever.get_knowledge_chunks(prefs, n=5)
    exercises = retriever.get_exercises(prefs)

    system_prompt = build_system_prompt(knowledge_chunks)
    user_prompt = build_user_prompt(prefs, exercises, knowledge_chunks)

    raw = await call_llm(system_prompt, user_prompt)
    plan = parse_plan(raw, prefs)

    critical, warnings = validate_volume(plan, prefs)

    if critical:
        hint = build_retry_hint(critical)
        raw = await call_llm(system_prompt, user_prompt, extra_hint=hint)
        plan = parse_plan(raw, prefs)
        _, warnings = validate_volume(plan, prefs)

    generation_ms = int((time.time() - t0) * 1000)

    result = plan.model_dump()
    result["_meta"] = {
        "warnings": warnings,
        "generation_ms": generation_ms,
        "exercises_retrieved": len(exercises),
        "knowledge_chunks_used": len(knowledge_chunks),
    }
    return result


@app.get("/health")
async def health() -> dict:
    db_loaded = retriever is not None
    return {
        "status": "ok",
        "db_loaded": db_loaded,
        "exercises_count": retriever.exercises.count() if db_loaded else 0,
        "knowledge_chunks": retriever.knowledge.count() if db_loaded else 0,
    }


@app.post("/ingest")
async def ingest_endpoint() -> dict:
    global retriever
    try:
        ex_count, kn_count = ingest(XLSX_PATH, DOCX_PATH, PDF_PATH, CHROMA_PATH)
        retriever = RAGRetriever(chroma_path=CHROMA_PATH)
        return {
            "status": "ok",
            "exercises_indexed": ex_count,
            "knowledge_chunks_indexed": kn_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Verifica che i test passino**

```powershell
python -m pytest tests/test_main.py -v
```

Output atteso: `8 passed`

- [ ] **Step 5: Verifica avvio server**

```powershell
uvicorn main:app --port 8000
```

In un altro terminale:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
```

Output atteso: `status: ok, db_loaded: True`

- [ ] **Step 6: Commit**

```powershell
git add backend/main.py backend/tests/test_main.py
git commit -m "feat: add FastAPI app with /generate /health /ingest endpoints"
```

---

## Task 9: Next.js Proxy

**Files:**
- Modify: `webapp/app/api/generate/route.ts`

- [ ] **Step 1: Aggiorna route.ts**

Sostituisci tutto il contenuto di `webapp/app/api/generate/route.ts` con:
```typescript
import { NextRequest, NextResponse } from 'next/server';

const PYTHON_API = process.env.PYTHON_API_URL ?? 'http://localhost:8000';

export async function POST(req: NextRequest) {
  const body = await req.json();

  let res: Response;
  try {
    res = await fetch(`${PYTHON_API}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(180_000),
    });
  } catch {
    return NextResponse.json({ error: 'Backend Python non raggiungibile.' }, { status: 503 });
  }

  const data = await res.json();
  if (!res.ok) {
    return NextResponse.json({ error: data.detail ?? 'Errore nella generazione.' }, { status: res.status });
  }
  return NextResponse.json(data);
}
```

- [ ] **Step 2: Aggiungi PYTHON_API_URL al .env.local di Next.js**

In `webapp/.env.local` (crea se non esiste):
```
PYTHON_API_URL=http://localhost:8000
```

- [ ] **Step 3: Cancella file TypeScript non più necessari**

```powershell
Remove-Item "C:\Users\andre\Desktop\prime next\webapp\lib\rag.ts"
Remove-Item "C:\Users\andre\Desktop\prime next\webapp\lib\exercises.ts"
```

- [ ] **Step 4: Verifica che Next.js si avvii ancora**

```powershell
cd "C:\Users\andre\Desktop\prime next\webapp"
npm run build
```

Output atteso: `✓ Compiled successfully` (nessun errore TypeScript)

Se ci sono errori di import da `rag.ts` o `exercises.ts` in altri file (es. workout page), rimuovi o aggiorna quegli import.

- [ ] **Step 5: Test integrazione completo**

Con entrambi i server attivi (FastAPI su :8000, Next.js su :3001):

```powershell
# Terminale 1
cd "C:\Users\andre\Desktop\prime next\backend"
uvicorn main:app --port 8000 --reload

# Terminale 2
cd "C:\Users\andre\Desktop\prime next\webapp"
npm run dev
```

Apri `http://localhost:3001`, compila il form e genera una scheda. Verifica:
1. La scheda viene generata e mostrata correttamente
2. I log FastAPI mostrano le chiamate a ChromaDB e OpenRouter
3. `_meta.exercises_retrieved` > 0 nella risposta (visibile nei log FastAPI)

- [ ] **Step 6: Commit finale**

```powershell
cd "C:\Users\andre\Desktop\prime next"
git add webapp/app/api/generate/route.ts webapp/.env.local
git commit -m "feat: replace TS generation logic with Python RAG proxy"
```

---

## Task 10: Test Suite Completa e Health Check

**Files:**
- Nessun file nuovo

- [ ] **Step 1: Esegui tutti i test**

```powershell
cd "C:\Users\andre\Desktop\prime next\backend"
python -m pytest tests/ -v --tb=short
```

Output atteso: `28+ passed, 0 failed`

- [ ] **Step 2: Test di carico manuale**

Genera 3 schede con lo stesso profilo e verifica che siano diverse:

```powershell
$body = '{"level":"intermedio","gender":"uomo","frequency":4,"targetMuscles":["petto","schiena"],"equipment":"palestra","notes":""}'

for ($i = 1; $i -le 3; $i++) {
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/generate" -Method Post -Body $body -ContentType "application/json"
    Write-Host "=== Scheda $i ==="
    Write-Host "Plan:" $resp.planName
    Write-Host "Day 1 exercises:" ($resp.days[0].exercises | ForEach-Object { $_.name }) -join ", "
    Write-Host "Warnings:" ($resp._meta.warnings -join "; ")
    Write-Host ""
}
```

Verifica: gli esercizi in pos. 5-6 (isolamenti) variano tra le 3 schede.

- [ ] **Step 3: Commit**

```powershell
git add -A
git commit -m "chore: full test suite passing, integration verified"
```

---

## Riepilogo File Creati

| File | Responsabilità |
|------|---------------|
| `backend/models.py` | Schema Pydantic — unica fonte di verità per tipi |
| `backend/rag/ingestion.py` | Parse .xlsx/.docx/.pdf, scoring SFR/ROM, ChromaDB |
| `backend/rag/retriever.py` | Semantic query, stochastic sampling, equipment filter |
| `backend/rag/prompt.py` | System + user prompt con rules evidence-based |
| `backend/validator.py` | MEV/MAV enforcement, retry hint |
| `backend/main.py` | FastAPI entrypoint, orchestrazione pipeline |
| `webapp/app/api/generate/route.ts` | Thin proxy → :8000 |

## Comandi di Avvio Rapido (dopo setup)

```powershell
# Backend
cd backend
uvicorn main:app --port 8000 --reload

# Frontend (terminale separato)
cd webapp
npm run dev
```
