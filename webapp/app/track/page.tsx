'use client';
import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import PerformanceChart from '@/components/PerformanceChart';
import type { WorkoutSession, UserSettings } from '@/lib/types';

export default function TrackPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [sessions, setSessions] = useState<WorkoutSession[]>([]);
  const [exercises, setExercises] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState('');

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return;
      setUserId(user.id);
      supabase.from('user_settings').select('*').eq('user_id', user.id).single()
        .then(({ data }) => setSettings(data));
    });
    fetch('/api/sessions').then(r => r.json()).then((data: WorkoutSession[]) => {
      const list = data ?? [];
      setSessions(list);
      const names = [...new Set(list.flatMap(s => s.exercises.map(e => e.name)))].sort();
      setExercises(names);
      if (names.length > 0) setSelected(names[0]);
      setLoading(false);
    });
  }, []);

  async function enableTracking() {
    const supabase = createClient();
    await supabase.from('user_settings').upsert({ user_id: userId, tracking_enabled: true });
    setSettings(prev => ({ ...(prev ?? { user_id: userId, updated_at: '' }), tracking_enabled: true }));
  }

  if (loading) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
      <p style={{ color: 'var(--ink-mute)' }}>Caricamento…</p>
    </div>;
  }

  if (!settings?.tracking_enabled) {
    return (
      <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>Performance tracking</h1>
        <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--ink-soft)', marginBottom: '1.5rem' }}>
            Abilita il tracking per visualizzare i tuoi progressi nel tempo.
          </p>
          <button className="btn-primary" onClick={enableTracking}>Abilita tracking</button>
        </div>
      </div>
    );
  }

  const thirtyDaysAgo = new Date(Date.now() - 30 * 864e5).toISOString().split('T')[0];
  const selectedSessions = sessions.filter(s => s.exercises.some(e => e.name === selected));
  const allWeights = selectedSessions.flatMap(s =>
    s.exercises.filter(e => e.name === selected).flatMap(e => e.sets.map(set => set.weight))
  );
  const maxWeight = allWeights.length > 0 ? Math.max(...allWeights) : 0;

  const recentW = selectedSessions.filter(s => s.session_date >= thirtyDaysAgo)
    .flatMap(s => s.exercises.filter(e => e.name === selected).flatMap(e => e.sets.map(set => set.weight)));
  const olderW = selectedSessions.filter(s => s.session_date < thirtyDaysAgo)
    .flatMap(s => s.exercises.filter(e => e.name === selected).flatMap(e => e.sets.map(set => set.weight)));
  const recentMax = recentW.length > 0 ? Math.max(...recentW) : 0;
  const olderMax = olderW.length > 0 ? Math.max(...olderW) : 0;
  const delta = olderMax > 0 ? (((recentMax - olderMax) / olderMax) * 100).toFixed(1) : null;

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '1.5rem' }}>Performance tracking</h1>

      {exercises.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--ink-soft)' }}>
            Nessuna sessione registrata. Vai su una scheda e premi &quot;Registra sessione&quot;.
          </p>
        </div>
      ) : (
        <>
          <select className="input-field" style={{ maxWidth: 300, marginBottom: '1.5rem' }}
            value={selected} onChange={e => setSelected(e.target.value)}>
            {exercises.map(n => <option key={n} value={n}>{n}</option>)}
          </select>

          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            {delta !== null && (
              <div className="card" style={{ padding: '1rem 1.5rem', flex: 1, minWidth: 120 }}>
                <span className="overline">Ultimi 30gg</span>
                <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem', color: Number(delta) >= 0 ? 'var(--green)' : '#dc2626' }}>
                  {Number(delta) >= 0 ? '+' : ''}{delta}%
                </p>
              </div>
            )}
            <div className="card" style={{ padding: '1rem 1.5rem', flex: 1, minWidth: 120 }}>
              <span className="overline">Massimo</span>
              <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem' }}>{maxWeight} kg</p>
            </div>
            <div className="card" style={{ padding: '1rem 1.5rem', flex: 1, minWidth: 120 }}>
              <span className="overline">Sessioni</span>
              <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem' }}>{selectedSessions.length}</p>
            </div>
          </div>

          <div className="card" style={{ padding: '1.5rem' }}>
            <PerformanceChart sessions={selectedSessions} exercise={selected} />
          </div>
        </>
      )}
    </div>
  );
}
