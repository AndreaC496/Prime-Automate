'use client';
import type { Exercise } from '@/lib/types';

interface Props {
  exercise: Exercise;
  onChange: (ex: Exercise) => void;
  onRemove: () => void;
  onReplace: () => void;
}

export default function ExerciseEditor({ exercise, onChange, onRemove, onReplace }: Props) {
  function update(field: keyof Exercise, value: string | number) {
    onChange({ ...exercise, [field]: value });
  }

  return (
    <div style={{ background: 'var(--surface-2)', borderRadius: 10, padding: '1rem', marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <strong style={{ fontSize: '0.95rem', color: 'var(--ink)' }}>{exercise.name}</strong>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button className="btn-secondary" style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }} onClick={onReplace}>
            Sostituisci
          </button>
          <button onClick={onRemove} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', fontSize: '1rem', padding: '0.25rem' }}>
            ✕
          </button>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
        {(['sets', 'reps', 'rest'] as const).map(field => (
          <div key={field}>
            <label style={{ display: 'block', fontSize: '0.65rem', color: 'var(--ink-mute)', marginBottom: '0.2rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              {field}
            </label>
            <input
              className="input-field"
              style={{ padding: '0.35rem 0.6rem', fontSize: '0.875rem' }}
              value={String(exercise[field])}
              onChange={e => update(field, field === 'sets' ? Number(e.target.value) : e.target.value)}
            />
          </div>
        ))}
      </div>
      <div style={{ marginTop: '0.5rem' }}>
        <label style={{ display: 'block', fontSize: '0.65rem', color: 'var(--ink-mute)', marginBottom: '0.2rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Note</label>
        <input
          className="input-field"
          style={{ padding: '0.35rem 0.6rem', fontSize: '0.875rem' }}
          value={exercise.notes}
          onChange={e => update('notes', e.target.value)}
          placeholder="Opzionale…"
        />
      </div>
    </div>
  );
}
