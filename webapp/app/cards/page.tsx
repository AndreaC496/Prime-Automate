import { createClient } from '@/lib/supabase/server';
import Link from 'next/link';
import WorkoutCardItem from '@/components/WorkoutCard';
import type { WorkoutCard } from '@/lib/types';

export default async function CardsPage() {
  const supabase = await createClient();
  const { data } = await supabase
    .from('workout_cards')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(3);

  const cards = (data ?? []) as WorkoutCard[];

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '2rem' }}>Le mie schede</h1>
        <Link href="/generate">
          <button className="btn-primary" style={{ padding: '0.6rem 1.2rem' }}>+ Nuova scheda</button>
        </Link>
      </div>

      {cards.length === 0 ? (
        <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--ink-soft)', marginBottom: '1.5rem' }}>Nessuna scheda ancora.</p>
          <Link href="/generate">
            <button className="btn-primary">Crea la tua prima scheda ⚡</button>
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {cards.map((card, idx) => (
            <WorkoutCardItem key={card.id} card={card} isActive={idx === 0} />
          ))}
        </div>
      )}
    </div>
  );
}
