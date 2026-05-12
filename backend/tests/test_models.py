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
