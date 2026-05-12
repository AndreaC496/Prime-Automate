'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/cards', label: 'Schede', icon: '📋' },
  { href: '/generate', label: 'Crea', icon: '✨' },
  { href: '/track', label: 'Tracking', icon: '📊' },
  { href: '/settings', label: 'Settings', icon: '⚙️' },
];

export default function Navbar() {
  const pathname = usePathname();
  if (pathname === '/') return null;

  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 50,
      backdropFilter: 'blur(20px)', background: 'rgba(255,255,255,.85)',
      borderTop: '1px solid rgba(22,163,74,.12)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-around', padding: '0.5rem 0 calc(0.75rem + env(safe-area-inset-bottom, 0px))' }}>
        {links.map(({ href, label, icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link key={href} href={href} style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
              textDecoration: 'none', padding: '0.4rem 1rem',
              color: active ? 'var(--green)' : 'var(--ink-mute)',
              fontFamily: "var(--font-barlow, 'Barlow Condensed', sans-serif)",
              fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.65rem',
              transition: 'color 0.15s',
            }}>
              <span style={{ fontSize: '1.25rem', lineHeight: 1 }}>{icon}</span>
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
