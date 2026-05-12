'use client';
import { useState } from 'react';
import type { WorkoutCardContent, Exercise } from '@/lib/types';
import ExerciseEditor from './ExerciseEditor';
import ExercisePicker from './ExercisePicker';

interface CardLike {
  content: WorkoutCardContent;
  inputs: { level: string; gender: string; frequency: number; muscles: string[]; notes: string };
}

interface Props {
  card: CardLike;
  mode: 'preview' | 'detail';
  onSave?: (content: WorkoutCardContent) => Promise<void>;
  onSessionLog?: () => void;
  onDownloadPDF?: () => void;
}

export default function WorkoutDetail({ card, mode, onSave, onSessionLog, onDownloadPDF }: Props) {
  const [editing, setEditing] = useState(mode === 'preview');
  const [content, setContent] = useState<WorkoutCardContent>(card.content);
  const [saving, setSaving] = useState(false);
  const [pickerFor, setPickerFor] = useState<{ dayIdx: number; exIdx: number } | null>(null);

  function updateExercise(dayIdx: number, exIdx: number, ex: Exercise) {
    setContent(prev => ({
      ...prev,
      days: prev.days.map((d, di) =>
        di === dayIdx ? { ...d, exercises: d.exercises.map((e, ei) => ei === exIdx ? ex : e) } : d
      ),
    }));
  }

  function removeExercise(dayIdx: number, exIdx: number) {
    setContent(prev => ({
      ...prev,
      days: prev.days.map((d, di) =>
        di === dayIdx ? { ...d, exercises: d.exercises.filter((_, ei) => ei !== exIdx) } : d
      ),
    }));
  }

  function addOrReplaceExercise(dayIdx: number, exIdx: number, name: string) {
    const day = content.days[dayIdx];
    if (exIdx < day.exercises.length) {
      updateExercise(dayIdx, exIdx, { ...day.exercises[exIdx], name });
    } else {
      const newEx: Exercise = { id: crypto.randomUUID(), name, sets: 3, reps: '10', rest: '90 sec', notes: '' };
      setContent(prev => ({
        ...prev,
        days: prev.days.map((d, di) =>
          di === dayIdx ? { ...d, exercises: [...d.exercises, newEx] } : d
        ),
      }));
    }
  }

  async function handleSave() {
    if (!onSave) return;
    setSaving(true);
    try { await onSave(content); setEditing(false); }
    finally { setSaving(false); }
  }

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '2.2rem', margin: '0 0 0.25rem' }}>{content.title}</h1>
        <p style={{ color: 'var(--ink-soft)', margin: 0 }}>{content.description}</p>
      </div>

      {mode === 'detail' && !editing && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <button className="btn-primary" onClick={() => setEditing(true)}>Modifica scheda</button>
          {onDownloadPDF && <button className="btn-secondary" onClick={onDownloadPDF}>Scarica PDF</button>}
          {onSessionLog && <button className="btn-secondary" onClick={onSessionLog}>Registra sessione</button>}
        </div>
      )}

      {editing && mode === 'detail' && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Salvataggio…' : 'Salva modifiche'}
          </button>
          <button className="btn-secondary" onClick={() => { setContent(card.content); setEditing(false); }}>Annulla</button>
        </div>
      )}

      {content.days.map((day, dayIdx) => (
        <div key={dayIdx} style={{ marginBottom: '2rem' }}>
          <div style={{ marginBottom: '0.75rem' }}>
            <span className="overline">{day.day}</span>
            <h2 style={{ margin: '0.2rem 0 0', fontSize: '1.3rem' }}>{day.label}</h2>
          </div>

          {editing ? (
            <>
              {day.exercises.map((ex, exIdx) => (
                <ExerciseEditor
                  key={ex.id}
                  exercise={ex}
                  onChange={e => updateExercise(dayIdx, exIdx, e)}
                  onRemove={() => removeExercise(dayIdx, exIdx)}
                  onReplace={() => setPickerFor({ dayIdx, exIdx })}
                />
              ))}
              <button className="btn-secondary" style={{ width: '100%', marginTop: '0.5rem', justifyContent: 'center' }}
                onClick={() => setPickerFor({ dayIdx, exIdx: day.exercises.length })}>
                + Aggiungi esercizio
              </button>
            </>
          ) : (
            day.exercises.map(ex => (
              <div key={ex.id} className="card" style={{ padding: '1rem', marginBottom: '0.65rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '1rem' }}>{ex.name}</strong>
                  <span style={{ fontSize: '0.85rem', color: 'var(--ink-soft)' }}>
                    {ex.sets}×{ex.reps} · {ex.rest}
                  </span>
                </div>
                {ex.notes && <p style={{ margin: '0.3rem 0 0', fontSize: '0.8rem', color: 'var(--ink-mute)' }}>{ex.notes}</p>}
              </div>
            ))
          )}
        </div>
      ))}

      {pickerFor !== null && (
        <ExercisePicker
          onSelect={name => addOrReplaceExercise(pickerFor!.dayIdx, pickerFor!.exIdx, name)}
          onClose={() => setPickerFor(null)}
        />
      )}
    </div>
  );
}
