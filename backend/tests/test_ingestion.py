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
