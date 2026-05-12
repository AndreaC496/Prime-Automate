export type Level = 'principiante' | 'intermedio' | 'avanzato';
export type Gender = 'uomo' | 'donna';

export interface Exercise {
  id: string;
  name: string;
  sets: number;
  reps: string;
  rest: string;
  notes: string;
}

export interface WorkoutDay {
  day: string;
  label: string;
  exercises: Exercise[];
}

export interface WorkoutCardContent {
  title: string;
  description: string;
  days: WorkoutDay[];
}

export interface WorkoutInputs {
  level: Level;
  gender: Gender;
  frequency: number;
  muscles: string[];
  notes: string;
}

export interface WorkoutCard {
  id: string;
  user_id: string;
  title: string;
  content: WorkoutCardContent;
  inputs: WorkoutInputs;
  created_at: string;
}

export interface SessionSet {
  weight: number;
  reps: number;
}

export interface SessionExercise {
  name: string;
  sets: SessionSet[];
}

export interface WorkoutSession {
  id: string;
  user_id: string;
  card_id: string | null;
  exercises: SessionExercise[];
  notes: string | null;
  session_date: string;
  created_at: string;
}

export interface UserSettings {
  user_id: string;
  tracking_enabled: boolean;
  updated_at: string;
}
