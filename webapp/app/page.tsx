import AuthForm from '@/components/AuthForm';

export default function AuthPage() {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '2rem',
    }}>
      <div style={{ marginBottom: '2.5rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '4.5rem', margin: 0, color: 'var(--ink)', letterSpacing: '-2px' }}>PRIME</h1>
        <p style={{ color: 'var(--ink-soft)', marginTop: '0.5rem', fontSize: '1rem' }}>Il tuo personal trainer AI</p>
      </div>
      <div className="card" style={{ width: '100%', maxWidth: 420, padding: '2rem' }}>
        <AuthForm />
      </div>
    </div>
  );
}
