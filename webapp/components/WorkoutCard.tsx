'use client';
import Link from 'next/link';
import type { WorkoutCard } from '@/lib/types';

interface Props {
  card: WorkoutCard;
  isActive: boolean;
}

export default function WorkoutCardItem({ card, isActive }: Props) {
  const allExercises = card.content.days.flatMap(d => d.exercises.map(e => e.name));
  const visible = allExercises.slice(0, 4);
  const extra = allExercises.length - visible.length;

  return (
    <Link href={`/cards/${card.id}`} style={{ textDecoration: 'none' }}>
      <div className="card" style={{ padding: '1.25rem', opacity: isActive ? 1 : 0.65 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
          <span className="overline">{isActive ? 'Attiva' : 'Storico'}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--ink-mute)' }}>
            {new Date(card.created_at).toLocaleDateString('it-IT')}
          </span>
        </div>
        <h3 style={{ margin: '0 0 0.2rem', fontSize: '1.4rem', color: 'var(--ink)' }}>{card.content.title}</h3>
        <p style={{ margin: '0 0 0.9rem', fontSize: '0.8rem', color: 'var(--ink-soft)' }}>
          {card.inputs.level} · {card.inputs.frequency}g/sett · {card.inputs.muscles.join(', ')}
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
          {visible.map(name => (
            <span key={name} className="exercise-chip">{name}</span>
          ))}
          {extra > 0 && <span className="exercise-chip">+{extra} altri</span>}
        </div>
      </div>
    </Link>
  );
}
