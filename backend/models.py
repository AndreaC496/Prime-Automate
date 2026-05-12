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
