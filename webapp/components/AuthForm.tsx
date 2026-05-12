'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

export default function AuthForm() {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const supabase = createClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (tab === 'login') {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
      }
      router.push('/cards');
      router.refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', marginBottom: '1.5rem', borderBottom: '2px solid rgba(22,163,74,.15)' }}>
        {(['login', 'register'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, padding: '0.75rem', background: 'none', border: 'none',
            borderBottom: tab === t ? '2px solid var(--green)' : '2px solid transparent',
            marginBottom: '-2px', cursor: 'pointer',
            fontFamily: "var(--font-barlow, 'Barlow Condensed', sans-serif)",
            fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px',
            color: tab === t ? 'var(--green)' : 'var(--ink-mute)',
          }}>
            {t === 'login' ? 'Accedi' : 'Registrati'}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--ink-soft)' }}>Email</label>
          <input className="input-field" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--ink-soft)' }}>Password</label>
          <input className="input-field" type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} />
          {error && <p style={{ color: '#dc2626', fontSize: '0.85rem', marginTop: '0.4rem' }}>{error}</p>}
        </div>
        <button className="btn-primary" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
          {loading ? 'Caricamento…' : tab === 'login' ? 'Accedi' : 'Registrati'}
        </button>
      </form>
    </div>
  );
}
