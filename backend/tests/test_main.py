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
