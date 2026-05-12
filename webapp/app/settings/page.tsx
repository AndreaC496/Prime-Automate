'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import type { UserSettings } from '@/lib/types';

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [userId, setUserId] = useState('');
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return;
      setUserId(user.id);
      supabase.from('user_settings').select('*').eq('user_id', user.id).single()
        .then(({ data }) => setSettings(data));
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function toggleTracking() {
    const newValue = !settings?.tracking_enabled;
    await supabase.from('user_settings').upsert({ user_id: userId, tracking_enabled: newValue });
    setSettings(prev => ({ ...(prev ?? { user_id: userId, updated_at: '' }), tracking_enabled: newValue }));
  }

  async function handleLogout() {
    await supabase.auth.signOut();
    router.push('/');
    router.refresh();
  }

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '2rem' }}>Impostazioni</h1>

      <div className="card" style={{ padding: '1.25rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <p style={{ margin: 0, fontWeight: 600, fontSize: '0.95rem' }}>Performance tracking</p>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: 'var(--ink-mute)' }}>Registra i progressi per esercizio</p>
        </div>
        <button onClick={toggleTracking} style={{
          width: 52, height: 28, borderRadius: 14, border: 'none', cursor: 'pointer',
          background: settings?.tracking_enabled ? 'var(--green)' : 'rgba(22,163,74,.2)',
          position: 'relative', transition: 'background 0.2s', flexShrink: 0,
        }}>
          <span style={{
            position: 'absolute', top: 3,
            left: settings?.tracking_enabled ? 26 : 3,
            width: 22, height: 22, borderRadius: '50%', background: '#fff',
            transition: 'left 0.2s', display: 'block',
            boxShadow: '0 1px 4px rgba(0,0,0,.2)',
          }} />
        </button>
      </div>

      <button className="btn-secondary" style={{ width: '100%', marginTop: '1.5rem', justifyContent: 'center' }} onClick={handleLogout}>
        Logout
      </button>
    </div>
  );
}
