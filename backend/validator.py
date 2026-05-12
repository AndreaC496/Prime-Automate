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
