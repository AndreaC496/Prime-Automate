'use client';
import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';

interface Props {
  onSelect: (name: string) => void;
  onClose: () => void;
}

export default function ExercisePicker({ onSelect, onClose }: Props) {
  const [exercises, setExercises] = useState<string[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const supabase = createClient();
    supabase
      .from('document_chunks')
      .select('metadata')
      .eq('doc_type', 'exercise')
      .then(({ data }) => {
        if (!data) return;
        const names = [...new Set(
          data.map((r: { metadata: Record<string, unknown> }) => r.metadata?.name as string).filter(Boolean)
        )].sort() as string[];
        setExercises(names);
      });
  }, []);

  const filtered = exercises.filter(e => e.toLowerCase().includes(search.toLowerCase()));

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 100, display: 'flex', alignItems: 'flex-end' }}>
      <div style={{ width: '100%', background: 'var(--surface)', borderRadius: '20px 20px 0 0', padding: '1.5rem', maxHeight: '70vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.4rem' }}>Scegli esercizio</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.4rem', cursor: 'pointer', color: 'var(--ink-mute)' }}>✕</button>
        </div>
        <input className="input-field" placeholder="Cerca…" value={search} onChange={e => setSearch(e.target.value)} style={{ marginBottom: '1rem' }} />
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {filtered.length === 0 && <p style={{ color: 'var(--ink-mute)', textAlign: 'center', padding: '1rem' }}>Nessun risultato.</p>}
          {filtered.map(name => (
            <button key={name} onClick={() => { onSelect(name); onClose(); }} style={{
              display: 'block', width: '100%', textAlign: 'left', padding: '0.75rem 1rem',
              background: 'none', border: 'none', borderBottom: '1px solid rgba(22,163,74,.08)',
              cursor: 'pointer', fontSize: '0.95rem', color: 'var(--ink)',
            }}>
              {name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
