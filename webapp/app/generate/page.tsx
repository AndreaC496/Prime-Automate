import GenerateWizard from '@/components/GenerateWizard';

export default function GeneratePage() {
  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.4rem' }}>Nuova scheda</h1>
      <p style={{ color: 'var(--ink-soft)', marginBottom: '2rem', marginTop: 0 }}>
        Rispondi a 5 domande e l&apos;AI crea la tua scheda personalizzata.
      </p>
      <GenerateWizard />
    </div>
  );
}
