'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { WorkoutInputs, WorkoutCardContent } from '@/lib/types';
import WorkoutDetail from './WorkoutDetail';

const MUSCLES = ['Petto', 'Schiena', 'Quadricipiti', 'Femorali', 'Glutei', 'Spalle', 'Bicipiti', 'Tricipiti', 'Full Body'];
const LOADING_MSGS = ['Analizzo i tuoi parametri…', 'Cerco gli esercizi migliori…', 'Costruisco la scheda…'];

type GenState = 'idle' | 'loading' | 'preview';

export default function GenerateWizard() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [inputs, setInputs] = useState<WorkoutInputs>({ level: 'intermedio', gender: 'uomo', frequency: 3, muscles: [], notes: '' });
  const [genState, setGenState] = useState<GenState>('idle');
  const [msgIdx, setMsgIdx] = useState(0);
  const [preview, setPreview] = useState<{ content: WorkoutCardContent; inputs: WorkoutInputs } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function generate() {
    setError('');
    setGenState('loading');
    setMsgIdx(0);
    const interval = setInterval(() => setMsgIdx(i => Math.min(i + 1, LOADING_MSGS.length - 1)), 1800);
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(inputs),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setPreview(data);
      setGenState('preview');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Errore nella generazione');
      setGenState('idle');
    } finally {
      clearInterval(interval);
    }
  }

  async function saveCard() {
    if (!preview) return;
    setSaving(true);
    try {
      const res = await fetch('/api/cards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preview),
      });
      const card = await res.json();
      router.push(`/cards/${card.id}`);
    } finally {
      setSaving(false);
    }
  }

  if (genState === 'loading') {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 2rem' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem', animation: 'pulse 1s infinite' }}>⚡</div>
        <p style={{ fontSize: '1.1rem', color: 'var(--ink-soft)' }}>{LOADING_MSGS[msgIdx]}</p>
      </div>
    );
  }

  if (genState === 'preview' && preview) {
    return (
      <div>
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <button className="btn-primary" onClick={saveCard} disabled={saving}>
            {saving ? 'Salvataggio…' : 'Salva scheda'}
          </button>
          <button className="btn-secondary" onClick={generate}>Rigenera</button>
        </div>
        <WorkoutDetail
          card={{ content: preview.content, inputs: preview.inputs }}
          mode="preview"
        />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 520, margin: '0 auto' }}>
      <div style={{ height: 4, background: 'rgba(22,163,74,.15)', borderRadius: 2, marginBottom: '2rem' }}>
        <div style={{ height: '100%', width: `${(step / 5) * 100}%`, background: 'var(--green)', borderRadius: 2, transition: 'width 0.3s' }} />
      </div>

      {error && <p style={{ color: '#dc2626', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</p>}

      {step === 1 && (
        <Step title="Livello" subtitle="Qual è la tua esperienza?">
          {(['principiante', 'intermedio', 'avanzato'] as const).map(l => (
            <button key={l} className={`pill ${inputs.level === l ? 'on' : ''}`}
              onClick={() => setInputs(p => ({ ...p, level: l }))}
              style={{ marginRight: '0.5rem', marginBottom: '0.5rem', textTransform: 'capitalize' }}>
              {l}
            </button>
          ))}
        </Step>
      )}

      {step === 2 && (
        <Step title="Sesso" subtitle="Come ti identifichi?">
          {(['uomo', 'donna'] as const).map(g => (
            <button key={g} className={`pill ${inputs.gender === g ? 'on' : ''}`}
              onClick={() => setInputs(p => ({ ...p, gender: g }))}
              style={{ marginRight: '0.5rem', textTransform: 'capitalize' }}>
              {g}
            </button>
          ))}
        </Step>
      )}

      {step === 3 && (
        <Step title="Frequenza" subtitle="Quanti giorni ti alleni a settimana?">
          {[2, 3, 4, 5].map(f => (
            <button key={f} className={`pill ${inputs.frequency === f ? 'on' : ''}`}
              onClick={() => setInputs(p => ({ ...p, frequency: f }))}
              style={{ marginRight: '0.5rem' }}>
              {f === 5 ? '5+ giorni' : `${f} giorni`}
            </button>
          ))}
        </Step>
      )}

      {step === 4 && (
        <Step title="Muscoli focus" subtitle="Seleziona uno o più gruppi muscolari.">
          {MUSCLES.map(m => (
            <button key={m}
              className={`pill ${inputs.muscles.includes(m) ? 'on' : ''}`}
              onClick={() => setInputs(p => ({
                ...p,
                muscles: p.muscles.includes(m) ? p.muscles.filter(x => x !== m) : [...p.muscles, m],
              }))}
              style={{ marginRight: '0.5rem', marginBottom: '0.5rem' }}>
              {m}
            </button>
          ))}
        </Step>
      )}

      {step === 5 && (
        <Step title="Note aggiuntive" subtitle="Attrezzatura limitata, infortuni, preferenze?">
          <textarea className="input-field" rows={4}
            placeholder="Es. no bilanciere, solo manubri, palestra casa…"
            value={inputs.notes}
            onChange={e => setInputs(p => ({ ...p, notes: e.target.value }))}
          />
        </Step>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem' }}>
        {step > 1
          ? <button className="btn-secondary" onClick={() => setStep(s => s - 1)}>Indietro</button>
          : <span />
        }
        {step < 5
          ? <button className="btn-primary" onClick={() => setStep(s => s + 1)} disabled={step === 4 && inputs.muscles.length === 0}>
              Avanti
            </button>
          : <button className="btn-primary" onClick={generate}>Genera scheda ⚡</button>
        }
      </div>
    </div>
  );
}

function Step({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="overline">Step</span>
      <h2 style={{ margin: '0.25rem 0 0.5rem', fontSize: '1.8rem' }}>{title}</h2>
      <p style={{ color: 'var(--ink-soft)', marginBottom: '1.5rem', marginTop: 0 }}>{subtitle}</p>
      <div>{children}</div>
    </div>
  );
}
