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
    # petto MEV intermedio = 12. Only 6 sets.
    plan = _make_plan([("Pettorali", 3), ("Pettorali", 3)], prefs)
    critical, warnings = validate_volume(plan, prefs)
    assert any("petto" in c for c in critical)


def test_validate_non_priority_below_mev_is_warning_only():
    prefs = _make_prefs(level="intermedio", muscles=["schiena"])
    # schiena has 15 sets (within MEV/MAV), petto not priority
    plan = _make_plan([("Gran dorsale", 15)], prefs)
    critical, warnings = validate_volume(plan, prefs)
    assert not any("schiena" in c for c in critical)


def test_validate_over_mav_is_warning():
    prefs = _make_prefs(level="intermedio", muscles=["petto"])
    # petto MAV intermedio = 16. 20 sets → over MAV
    plan = _make_plan([("Pettorali", 5)] * 4, prefs)
    _, warnings = validate_volume(plan, prefs)
    assert any("petto" in w for w in warnings)


def test_validate_within_range_no_violations():
    prefs = _make_prefs(level="intermedio", muscles=["petto"])
    # petto MEV=12 MAV=16. 14 sets → within range
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
