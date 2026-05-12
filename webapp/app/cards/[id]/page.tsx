'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import type { WorkoutCard, WorkoutCardContent } from '@/lib/types';
import WorkoutDetail from '@/components/WorkoutDetail';
import SessionModal from '@/components/SessionModal';

export default function CardDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [card, setCard] = useState<WorkoutCard | null>(null);
  const [showSession, setShowSession] = useState(false);

  useEffect(() => {
    fetch('/api/cards')
      .then(r => r.json())
      .then((cards: WorkoutCard[]) => {
        const found = cards.find(c => c.id === id);
        if (found) setCard(found);
        else router.push('/cards');
      });
  }, [id, router]);

  if (!card) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <p style={{ color: 'var(--ink-mute)' }}>Caricamento…</p>
      </div>
    );
  }

  async function handleSave(content: WorkoutCardContent) {
    const res = await fetch(`/api/cards/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    const updated = await res.json();
    setCard(updated);
  }

  async function handleDownloadPDF() {
    const { generatePDF } = await import('@/lib/pdf');
    await generatePDF(card!);
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
      <button onClick={() => router.push('/cards')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--green)', marginBottom: '1.25rem', fontSize: '0.9rem',
        display: 'flex', alignItems: 'center', gap: '0.3rem', padding: 0,
      }}>
        ← Le mie schede
      </button>
      <WorkoutDetail
        card={card}
        mode="detail"
        onSave={handleSave}
        onSessionLog={() => setShowSession(true)}
        onDownloadPDF={handleDownloadPDF}
      />
      {showSession && <SessionModal card={card} onClose={() => setShowSession(false)} />}
    </div>
  );
}
