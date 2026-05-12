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

    raise ValueError("Unterminated JSON object in model response")


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
    choices = data.get("choices") or []
    if not choices:
        raise ValueError(f"Unexpected LLM response: {data}")
    content = choices[0]["message"]["content"]
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
