'use client';
import { useState } from 'react';
import type { WorkoutCard, SessionExercise, SessionSet } from '@/lib/types';

interface Props {
  card: WorkoutCard;
  onClose: () => void;
}

export default function SessionModal({ card, onClose }: Props) {
  const allExercises = card.content.days.flatMap(d => d.exercises);
  const [exercises, setExercises] = useState<SessionExercise[]>(
    allExercises.map(ex => ({
      name: ex.name,
      sets: Array.from({ length: ex.sets }, () => ({ weight: 0, reps: 0 })),
    }))
  );
  const [notes, setNotes] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [saving, setSaving] = useState(false);

  function updateSet(exIdx: number, setIdx: number, field: keyof SessionSet, value: number) {
    setExercises(prev => prev.map((ex, i) =>
      i === exIdx
        ? { ...ex, sets: ex.sets.map((s, j) => j === setIdx ? { ...s, [field]: value } : s) }
        : ex
    ));
  }

  async function handleSubmit() {
    setSaving(true);
    try {
      await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card_id: card.id, exercises, notes, session_date: date }),
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 100, overflowY: 'auto' }}>
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '2rem 1rem' }}>
        <div style={{ background: 'var(--surface)', borderRadius: 16, padding: '1.5rem', width: '100%', maxWidth: 560 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.5rem' }}>Registra sessione</h2>
            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.4rem', cursor: 'pointer', color: 'var(--ink-mute)' }}>✕</button>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--ink-soft)' }}>Data</label>
            <input className="input-field" type="date" value={date} onChange={e => setDate(e.target.value)} />
          </div>

          {exercises.map((ex, exIdx) => (
            <div key={exIdx} style={{ marginBottom: '1.25rem' }}>
              <p style={{ margin: '0 0 0.5rem', fontWeight: 600, fontSize: '0.95rem' }}>{ex.name}</p>
              {ex.sets.map((s, setIdx) => (
                <div key={setIdx} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--ink-mute)' }}>Set {setIdx + 1}</span>
                  <input className="input-field" style={{ padding: '0.4rem 0.6rem' }} type="number" placeholder="kg"
                    value={s.weight || ''} onChange={e => updateSet(exIdx, setIdx, 'weight', Number(e.target.value))} />
                  <input className="input-field" style={{ padding: '0.4rem 0.6rem' }} type="number" placeholder="reps"
                    value={s.reps || ''} onChange={e => updateSet(exIdx, setIdx, 'reps', Number(e.target.value))} />
                </div>
              ))}
            </div>
          ))}

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--ink-soft)' }}>Note sessione</label>
            <textarea className="input-field" rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Come è andata?" />
          </div>

          <button className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={handleSubmit} disabled={saving}>
            {saving ? 'Salvataggio…' : 'Salva sessione'}
          </button>
        </div>
      </div>
    </div>
  );
}
