# Python RAG Backend — Design Spec
**Date:** 2026-05-12  
**Status:** Approved  

---

## Obiettivo

Rimpiazzare la logica di generazione attuale (TypeScript route + injection statica di tutti gli esercizi) con un microservizio FastAPI Python che implementa un RAG semantico reale: embeddings su esercizi (.xlsx) e knowledge base scientifica (.docx + info.pdf), retrieval contestuale, e validazione del volume post-generazione.

---

## Architettura

```
prime next/
├── webapp/                          (Next.js, invariato)
│   └── app/api/generate/route.ts   ← thin proxy verso :8000
│
└── backend/                         (NUOVO)
    ├── main.py                      (FastAPI app)
    ├── rag/
    │   ├── ingestion.py             (legge .xlsx, .docx, .pdf → ChromaDB)
    │   ├── retriever.py             (query semantica → chunks + esercizi scored)
    │   └── prompt.py                (costruisce prompt arricchito)
    ├── validator.py                 (controlla MEV/MAV/MRV post-generazione)
    ├── models.py                    (Pydantic: UserPreferences, WorkoutPlan)
    ├── db/                          (ChromaDB persistent storage)
    └── requirements.txt
```

### Data flow per request

```
Client → Next.js /api/generate (proxy)
  → POST http://localhost:8000/generate
  → [retriever] query embedding → ChromaDB
      ├── top-5 knowledge chunks (da .docx + info.pdf)
      └── top-20 esercizi scored (da .xlsx)
  → [prompt] system + user prompt arricchito
  → OpenRouter Nemotron 3 Super 120B → JSON
  → [validator] controlla volume MEV/MAV
      └── se violation critica: 1 retry con hint
  → WorkoutPlan → Next.js → Client
```

---

## RAG Pipeline

### 1. Ingestion (one-time, rebuild via POST /ingest)

**ChromaDB collection: `exercises`**
- Sorgente: `set esercizi.xlsx`
- Ogni riga = un esercizio con campi: name, primaryMuscle, secondaryMuscles, category, equipment, homeGym, sfr_score, rom_score (colonne attese; se assenti, stimate da regole)
- Embedding: `paraphrase-multilingual-MiniLM-L12-v2` (locale, ~120MB, ottimizzato per italiano)
- Document text: `"{name} | {primaryMuscle} | {category} | {equipment}"` + campi extra come metadata

**ChromaDB collection: `knowledge`**
- Sorgente: `indicazioni schede.docx` + `info.pdf`
- Chunking: 300 token con overlap 50 (paragrafi semantici, non semplice split)
- Ogni chunk = documento con metadata: source_file, section_title
- Embedding: stesso modello

### 2. Retrieval per request

**Query di recupero costruita dai parametri utente:**
```python
query = f"{level} {gender} {' '.join(targetMuscles)} {equipment} allenamento scheda"
```

**Esercizi — Stochastic Scored Sampling:**

Per ogni esercizio nel pool (filtrato per equipment):
```python
composite_score = (
    sfr_score       * 0.30 +   # Stimulus/Fatigue Ratio
    rom_score       * 0.30 +   # posizione allungata (Maeo 2023)
    semantic_score  * 0.25 +   # cosine similarity con query utente
    priority_bonus  * 0.15     # muscolo in targetMuscles? +0.15
)
```

Campionamento probabilistico con temperature per categoria:
- **Pos 1-2 (compound bilanciere):** T=0.3 → sempre i best, poca variabilità
- **Pos 3-4 (compound accessori):** T=0.6 → variabilità media
- **Pos 5-6 (isolamenti):** T=1.0 → alta variabilità, tutti i validi possono uscire

Questo garantisce schede sempre di alto livello (esercizi con score basso hanno probabilità minima) ma diverse ad ogni generazione.

**Knowledge chunks:**
- Top-5 chunk per cosine similarity alla query
- Injected nel system prompt come `=== LINEE GUIDA CONTESTUALI ===`

### 3. Prompt construction

Il system prompt Python estende l'attuale con:
- Sezione `=== LINEE GUIDA CONTESTUALI ===`: i 5 chunk recuperati dal .docx/pdf
- Sezione `=== ESERCIZI DISPONIBILI ===`: i top-20 scored (non tutti), con score metadata visibile al LLM

Il user prompt è lo stesso struttura dell'attuale (level, gender, frequency, split advice, volume targets, set/rep structure) ma con esercizi già pre-selezionati e ranked.

---

## Volume Validator

Tabella MEV/MAV (da Schoenfeld 2017, RP Israetel) hardcoded in Python:

```python
MEV_MAV = {
  "principiante": {
    "petto": (6, 10), "schiena": (8, 12), "spalle": (8, 12),
    "bicipiti": (6, 8), "tricipiti": (6, 8),
    "quadricipiti": (8, 10), "femorali": (6, 8), "glutei": (4, 8)
  },
  "intermedio": {
    "petto": (12, 16), "schiena": (14, 18), "spalle": (12, 16),
    "bicipiti": (12, 14), "tricipiti": (10, 12),
    "quadricipiti": (12, 14), "femorali": (10, 12), "glutei": (6, 10)
  },
  "avanzato": {
    "petto": (16, 20), "schiena": (18, 22), "spalle": (16, 22),
    "bicipiti": (14, 20), "tricipiti": (12, 14),
    "quadricipiti": (14, 18), "femorali": (12, 16), "glutei": (10, 14)
  }
}
```

**Logica:**
1. Conta set per gruppo muscolare nel piano generato (mappando primaryMuscle → categoria)
2. Confronta con MEV/MAV per il livello utente
3. Se un muscolo **prioritario** (in targetMuscles) è sotto MEV: 1 retry con hint specifico nel prompt
4. Violations non critiche (muscoli non prioritari, o over-MAV lieve): aggiunte a `_meta.warnings`

---

## API Contract

```
POST /generate
Content-Type: application/json
Body: {
  "level": "intermedio",
  "gender": "uomo",
  "frequency": 4,
  "targetMuscles": ["petto", "schiena"],
  "equipment": "palestra",
  "notes": ""
}

Response 200: WorkoutPlan (schema identico al TypeScript attuale)
  + "_meta": {
      "warnings": ["femorali: 8 set < MEV (10)"],
      "generation_ms": 1840,
      "exercises_retrieved": 20,
      "knowledge_chunks_used": 5
    }

GET /health
Response: { "status": "ok", "db_loaded": true, "exercises_count": N, "knowledge_chunks": M }

POST /ingest
Response: { "status": "ok", "exercises_indexed": N, "knowledge_chunks_indexed": M }
```

---

## Modifica Next.js (route.ts)

La route TypeScript diventa un thin proxy (~10 righe):

```typescript
export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch('http://localhost:8000/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) return NextResponse.json({ error: data.error }, { status: res.status });
  return NextResponse.json(data);
}
```

La logica di `snapExercise`, `filterExercises`, `buildSystemPrompt`, `buildUserPrompt` si sposta nel Python. I file `rag.ts` e la parte di logica in `route.ts` vengono eliminati.

---

## Stack Python

```
fastapi>=0.115
uvicorn[standard]
chromadb>=0.5
sentence-transformers>=3.0
python-docx
openpyxl
pymupdf          # lettura info.pdf
httpx            # chiamate OpenRouter
pydantic>=2.0
python-dotenv
```

---

## SFR e ROM Score — Stima automatica

Se il file .xlsx non ha colonne `sfr_score`/`rom_score`, il sistema le stima con regole:

**ROM Score** (0.0–1.0):
- Esercizi in posizione allungata (overhead ext, incline curl, leg curl seduto, hip thrust): 0.9
- Esercizi multi-articolari full ROM (squat, deadlift, pull-up): 0.8
- Esercizi con ROM medio (lat machine, rematore): 0.6
- Esercizi con ROM corto (pushdown, alzate laterali): 0.4

**SFR Score** (0.0–1.0):
- Macchine isolation (leg extension, peck fly, cable crossover): 0.9 (alto stimolo, bassa fatica)
- Manubri/cavi isolation: 0.8
- Compound macchina (chest press, shoulder press machine): 0.7
- Compound bilanciere (squat, bench press): 0.5 (alto stimolo MA alta fatica sistemica)

---

## Note implementative

- ChromaDB persiste su disco (`backend/db/`) — ingest run once, poi persist
- Il modello sentence-transformers viene scaricato al primo avvio (~120MB cache locale)
- OPENROUTER_API_KEY letto da `.env` (stesso file dell'attuale webapp)
- Avvio development: `uvicorn main:app --reload --port 8000`
- Il Next.js continua su porta 3001 (nessuna modifica)
