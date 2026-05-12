'use client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { WorkoutSession } from '@/lib/types';

interface Props {
  sessions: WorkoutSession[];
  exercise: string;
}

export default function PerformanceChart({ sessions, exercise }: Props) {
  const data = sessions
    .filter(s => s.exercises.some(e => e.name === exercise))
    .map(s => {
      const ex = s.exercises.find(e => e.name === exercise)!;
      const maxWeight = Math.max(...ex.sets.map(set => set.weight));
      return { date: s.session_date, weight: maxWeight };
    });

  if (data.length === 0) {
    return <p style={{ color: 'var(--ink-mute)', textAlign: 'center', padding: '2rem' }}>Nessun dato ancora.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(22,163,74,.1)" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--ink-mute)' }} />
        <YAxis tick={{ fontSize: 11, fill: 'var(--ink-mute)' }} unit=" kg" />
        <Tooltip
          formatter={(v) => [`${v} kg`, 'Peso max']}
          contentStyle={{ background: 'var(--surface)', border: '1px solid rgba(22,163,74,.2)', borderRadius: 8 }}
        />
        <Bar dataKey="weight" fill="var(--green)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
