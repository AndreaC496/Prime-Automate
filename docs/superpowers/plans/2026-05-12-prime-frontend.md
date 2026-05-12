# Prime Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Prime training card generator webapp — Next.js 15 with auth, RAG-powered workout generation, inline editing, PDF export, and performance tracking.

**Architecture:** Next.js 15 App Router in `webapp/`, Supabase for auth + DB + vector search via `match_documents` RPC, OpenRouter for LLM + embedding. Six pages, nine components, five API route groups. Middleware protects all routes except `/`.

**Tech Stack:** Next.js 15, TypeScript, Tailwind CSS, `@supabase/ssr`, Recharts, jsPDF, Google Fonts (Barlow Condensed + DM Sans), OpenRouter

---

## File Map

```
webapp/
├── app/
│   ├── globals.css
│   ├── layout.tsx
│   ├── page.tsx                     # / auth
│   ├── cards/page.tsx               # /cards list
│   ├── cards/[id]/page.tsx          # /cards/[id] detail
│   ├── generate/page.tsx            # /generate wizard
│   ├── track/page.tsx               # /track charts
│   ├── settings/page.tsx            # /settings
│   └── api/
│       ├── generate/route.ts
│       ├── cards/route.ts
│       ├── cards/[id]/route.ts
│       └── sessions/route.ts
├── components/
│   ├── AuthForm.tsx
│   ├── Navbar.tsx
│   ├── WorkoutCard.tsx
│   ├── WorkoutDetail.tsx
│   ├── ExerciseEditor.tsx
│   ├── ExercisePicker.tsx
│   ├── GenerateWizard.tsx
│   ├── SessionModal.tsx
│   └── PerformanceChart.tsx
├── lib/
│   ├── types.ts
│   ├── supabase/client.ts
│   ├── supabase/server.ts
│   ├── supabase/admin.ts
│   ├── openrouter.ts
│   ├── rag.ts
│   └── pdf.ts
└── middleware.ts
```

---

## Task 1: Scaffold + install deps + .env.local

- [ ] **Step 1: Create app**
```bash
cd "C:\Users\andre\Desktop\prime next"
npx create-next-app@15 webapp --typescript --tailwind --app --no-src-dir --import-alias "@/*" --eslint
```

- [ ] **Step 2: Install deps**
```bash
cd webapp
npm install @supabase/ssr @supabase/supabase-js recharts jspdf
```

- [ ] **Step 3: Create `webapp/.env.local`**
```
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key-from-supabase-dashboard>
SUPABASE_SERVICE_KEY=<service-role-key-from-supabase-dashboard>
OPENROUTER_LLM_KEY=<sk-or-v1-...>
OPENROUTER_LLM_MODEL=openai/gpt-oss-120b:free
OPENROUTER_EMBED_KEY=<sk-or-v1-...>
EMBED_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
```

- [ ] **Step 4: Verify build**
```bash
cd webapp && npm run build
```
Expected: succeeds, no TS errors.

- [ ] **Step 5: Commit**
```bash
git add webapp/
git commit -m "chore: scaffold Next.js 15 webapp"
```

---

## Task 2: Apply Supabase DB migration

- [ ] **Step 1: Apply migration via Supabase MCP (or SQL editor)**

Run in Supabase SQL editor at https://supabase.com/dashboard/project/cmtplysufbgslmpygbfz/sql:

```sql
create table if not exists workout_cards (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid references auth.users not null,
  title      text not null,
  content    jsonb not null,
  inputs     jsonb not null,
  created_at timestamptz default now()
);

create table if not exists workout_sessions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references auth.users not null,
  card_id      uuid references workout_cards on delete set null,
  exercises    jsonb not null,
  notes        text,
  session_date date not null default current_date,
  created_at   timestamptz default now()
);

create table if not exists user_settings (
  user_id          uuid primary key references auth.users,
  tracking_enabled boolean default false,
  updated_at       timestamptz default now()
);

alter table workout_cards enable row level security;
alter table workout_sessions enable row level security;
alter table user_settings enable row level security;

create policy "users own cards" on workout_cards
  for all using (auth.uid() = user_id);
create policy "users own sessions" on workout_sessions
  for all using (auth.uid() = user_id);
create policy "users own settings" on user_settings
  for all using (auth.uid() = user_id);
```

- [ ] **Step 2: Verify tables exist**
Run: `select table_name from information_schema.tables where table_schema='public';`
Expected: `workout_cards`, `workout_sessions`, `user_settings` present.

---

## Task 3: Types + Supabase clients + middleware

**Files:** `webapp/lib/types.ts`, `webapp/lib/supabase/client.ts`, `webapp/lib/supabase/server.ts`, `webapp/lib/supabase/admin.ts`, `webapp/middleware.ts`

- [ ] **Step 1: Create `webapp/lib/types.ts`**
```typescript
export type Level = 'principiante' | 'intermedio' | 'avanzato';
export type Gender = 'uomo' | 'donna';

export interface Exercise {
  id: string;
  name: string;
  sets: number;
  reps: string;
  rest: string;
  notes: string;
}

export interface WorkoutDay {
  day: string;
  label: string;
  exercises: Exercise[];
}

export interface WorkoutCardContent {
  title: string;
  description: string;
  days: WorkoutDay[];
}

export interface WorkoutInputs {
  level: Level;
  gender: Gender;
  frequency: number;
  muscles: string[];
  notes: string;
}

export interface WorkoutCard {
  id: string;
  user_id: string;
  title: string;
  content: WorkoutCardContent;
  inputs: WorkoutInputs;
  created_at: string;
}

export interface SessionSet {
  weight: number;
  reps: number;
}

export interface SessionExercise {
  name: string;
  sets: SessionSet[];
}

export interface WorkoutSession {
  id: string;
  user_id: string;
  card_id: string | null;
  exercises: SessionExercise[];
  notes: string | null;
  session_date: string;
  created_at: string;
}

export interface UserSettings {
  user_id: string;
  tracking_enabled: boolean;
  updated_at: string;
}
```

- [ ] **Step 2: Create `webapp/lib/supabase/client.ts`**
```typescript
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

- [ ] **Step 3: Create `webapp/lib/supabase/server.ts`**
```typescript
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll(); },
        setAll(list) {
          try { list.forEach(({ name, value, options }) => cookieStore.set(name, value, options)); }
          catch {}
        },
      },
    }
  );
}
```

- [ ] **Step 4: Create `webapp/lib/supabase/admin.ts`**
```typescript
import { createClient as base } from '@supabase/supabase-js';

export function createAdminClient() {
  return base(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_KEY!
  );
}
```

- [ ] **Step 5: Create `webapp/middleware.ts`**
```typescript
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll(); },
        setAll(list) {
          list.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          list.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();
  const { pathname } = request.nextUrl;

  if (!user && pathname !== '/') {
    return NextResponse.redirect(new URL('/', request.url));
  }
  if (user && pathname === '/') {
    return NextResponse.redirect(new URL('/cards', request.url));
  }
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api/).*)'],
};
```

- [ ] **Step 6: Type-check**
```bash
cd webapp && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 7: Commit**
```bash
git add webapp/lib webapp/middleware.ts
git commit -m "feat: add types, Supabase clients, auth middleware"
```

---

## Task 4: Design system + layout + Navbar

**Files:** `webapp/app/globals.css`, `webapp/app/layout.tsx`, `webapp/components/Navbar.tsx`

- [ ] **Step 1: Replace `webapp/app/globals.css`**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg: #DCFCE7;
  --surface: #ffffff;
  --surface-2: #F0FDF4;
  --ink: #0F1F14;
  --ink-soft: #374151;
  --ink-mute: #9CA3AF;
  --green: #16A34A;
  --green-mid: #22C55E;
  --green-bright: #4ADE80;
  --green-glow: rgba(22, 163, 74, 0.15);
  --shadow-green: 0 4px 20px rgba(22, 163, 74, 0.25);
  --shadow-card: 0 4px 16px rgba(15, 31, 20, 0.10);
}

* { box-sizing: border-box; }

body {
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-dm), 'DM Sans', sans-serif;
}

h1, h2, h3, .display {
  font-family: var(--font-barlow), 'Barlow Condensed', sans-serif;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: -0.01em;
}

.overline {
  font-family: var(--font-barlow), 'Barlow Condensed', sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 2.5px;
  color: var(--green);
  font-size: 0.7rem;
}

.card {
  background: var(--surface);
  border-radius: 14px;
  box-shadow: var(--shadow-card);
  transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(15,31,20,.14); }

.btn-primary {
  background: var(--green);
  color: #fff;
  font-family: var(--font-barlow), 'Barlow Condensed', sans-serif;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-radius: 10px;
  padding: 0.75rem 1.5rem;
  box-shadow: var(--shadow-green);
  border: none;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(22,163,74,.35); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.btn-secondary {
  background: transparent;
  color: var(--green);
  border: 1.5px solid var(--green);
  font-family: var(--font-barlow), 'Barlow Condensed', sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-radius: 10px;
  padding: 0.7rem 1.4rem;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-secondary:hover { background: var(--green-glow); }

.pill {
  display: inline-flex;
  align-items: center;
  border: 1.5px solid rgba(22,163,74,.35);
  border-radius: 20px;
  padding: 0.4rem 1rem;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--surface);
  color: var(--ink-soft);
}
.pill.on {
  background: var(--green);
  color: #fff;
  border-color: var(--green);
}

.input-field {
  width: 100%;
  border: 1.5px solid rgba(15,31,20,.15);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  font-family: var(--font-dm), 'DM Sans', sans-serif;
  font-size: 0.95rem;
  background: var(--surface);
  color: var(--ink);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.input-field:focus {
  border-color: var(--green);
  box-shadow: 0 0 0 4px var(--green-glow);
}

.exercise-chip {
  background: var(--surface-2);
  border: 1px solid rgba(22,163,74,.2);
  border-radius: 8px;
  padding: 0.3rem 0.7rem;
  font-size: 0.8rem;
  transition: background 0.15s;
}
.exercise-chip:hover { background: var(--green-glow); }
```

- [ ] **Step 2: Replace `webapp/app/layout.tsx`**
```tsx
import type { Metadata } from 'next';
import { Barlow_Condensed, DM_Sans } from 'next/font/google';
import './globals.css';
import Navbar from '@/components/Navbar';

const barlow = Barlow_Condensed({
  subsets: ['latin'],
  weight: ['700', '800', '900'],
  variable: '--font-barlow',
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-dm',
});

export const metadata: Metadata = {
  title: 'Prime',
  description: 'AI-powered training card generator',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it" className={`${barlow.variable} ${dmSans.variable}`}>
      <body>
        <main style={{ paddingBottom: '5rem' }}>{children}</main>
        <Navbar />
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Create `webapp/components/Navbar.tsx`**
```tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/cards', label: 'Schede', icon: '📋' },
  { href: '/generate', label: 'Crea', icon: '✨' },
  { href: '/track', label: 'Tracking', icon: '📊' },
  { href: '/settings', label: 'Impostazioni', icon: '⚙️' },
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
      <div style={{ display: 'flex', justifyContent: 'space-around', padding: '0.5rem 0 0.75rem' }}>
        {links.map(({ href, label, icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link key={href} href={href} style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px',
              textDecoration: 'none', padding: '0.4rem 1rem',
              color: active ? 'var(--green)' : 'var(--ink-mute)',
              fontFamily: 'var(--font-barlow, Barlow Condensed)', fontWeight: 700,
              textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.7rem',
              transition: 'color 0.15s',
            }}>
              <span style={{ fontSize: '1.3rem' }}>{icon}</span>
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Type-check**
```bash
cd webapp && npx tsc --noEmit
```

- [ ] **Step 5: Commit**
```bash
git add webapp/app/globals.css webapp/app/layout.tsx webapp/components/Navbar.tsx
git commit -m "feat: design system, layout, navbar"
```

---

## Task 5: Auth page + AuthForm

**Files:** `webapp/app/page.tsx`, `webapp/components/AuthForm.tsx`

- [ ] **Step 1: Create `webapp/components/AuthForm.tsx`**
```tsx
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
    } catch (err: any) {
      setError(err.message ?? 'Errore sconosciuto');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: '0 auto' }}>
      <div style={{ display: 'flex', marginBottom: '1.5rem', borderBottom: '2px solid rgba(22,163,74,.15)' }}>
        {(['login', 'register'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, padding: '0.75rem', background: 'none', border: 'none',
            borderBottom: tab === t ? '2px solid var(--green)' : '2px solid transparent',
            marginBottom: '-2px', cursor: 'pointer',
            fontFamily: 'var(--font-barlow, Barlow Condensed)', fontWeight: 700,
            textTransform: 'uppercase', letterSpacing: '1px',
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
        <button className="btn-primary" type="submit" disabled={loading}>
          {loading ? 'Caricamento…' : tab === 'login' ? 'Accedi' : 'Registrati'}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Create `webapp/app/page.tsx`**
```tsx
import AuthForm from '@/components/AuthForm';

export default function AuthPage() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
      <div style={{ marginBottom: '2.5rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '4rem', margin: 0, color: 'var(--ink)' }}>PRIME</h1>
        <p style={{ color: 'var(--ink-soft)', marginTop: '0.5rem' }}>Il tuo personal trainer AI</p>
      </div>
      <div className="card" style={{ width: '100%', maxWidth: 420, padding: '2rem' }}>
        <AuthForm />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/app/page.tsx webapp/components/AuthForm.tsx
git commit -m "feat: auth page with login/register form"
```

---

## Task 6: OpenRouter + RAG utils

**Files:** `webapp/lib/openrouter.ts`, `webapp/lib/rag.ts`

- [ ] **Step 1: Create `webapp/lib/openrouter.ts`**
```typescript
export async function callLLM(prompt: string): Promise<string> {
  const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.OPENROUTER_LLM_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: process.env.OPENROUTER_LLM_MODEL ?? 'openai/gpt-oss-120b:free',
      messages: [{ role: 'user', content: prompt }],
      response_format: { type: 'json_object' },
    }),
  });
  if (!res.ok) throw new Error(`LLM ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return data.choices[0].message.content as string;
}

export async function getEmbedding(text: string): Promise<number[]> {
  const res = await fetch('https://openrouter.ai/api/v1/embeddings', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.OPENROUTER_EMBED_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: process.env.EMBED_MODEL ?? 'nvidia/llama-nemotron-embed-vl-1b-v2:free',
      input: [text],
    }),
  });
  if (!res.ok) throw new Error(`Embed ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return data.data[0].embedding as number[];
}
```

- [ ] **Step 2: Create `webapp/lib/rag.ts`**
```typescript
import { createAdminClient } from './supabase/admin';
import { getEmbedding } from './openrouter';
import type { WorkoutInputs } from './types';

export function buildQuery(inputs: WorkoutInputs): string {
  return `esercizi ${inputs.muscles.join(' ')} ${inputs.level} ${inputs.gender} forza allenamento`;
}

export async function callMatchDocuments(
  query: string,
  topK = 12
): Promise<Array<{ content: string; doc_type: string }>> {
  const embedding = await getEmbedding(query);
  const supabase = createAdminClient();
  const { data, error } = await supabase.rpc('match_documents', {
    query_embedding: embedding,
    query_text: query,
    filter_metadata: {},
    match_count: topK,
  });
  if (error) throw new Error(`match_documents: ${error.message}`);
  return (data ?? []) as Array<{ content: string; doc_type: string }>;
}
```

- [ ] **Step 3: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/lib/openrouter.ts webapp/lib/rag.ts
git commit -m "feat: OpenRouter LLM + RAG utils"
```

---

## Task 7: API routes

**Files:** `webapp/app/api/generate/route.ts`, `webapp/app/api/cards/route.ts`, `webapp/app/api/cards/[id]/route.ts`, `webapp/app/api/sessions/route.ts`

- [ ] **Step 1: Create `webapp/app/api/generate/route.ts`**
```typescript
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { buildQuery, callMatchDocuments } from '@/lib/rag';
import { callLLM } from '@/lib/openrouter';
import type { WorkoutInputs, WorkoutCardContent } from '@/lib/types';

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const inputs: WorkoutInputs = await request.json();
  const query = buildQuery(inputs);
  const chunks = await callMatchDocuments(query, 12);
  const ragContext = chunks.map(c => c.content).join('\n\n---\n\n');

  const prompt = `Sei un personal trainer esperto. Genera una scheda di allenamento personalizzata in JSON.

CONTESTO DAL DATABASE ESERCIZI E LINEE GUIDA:
${ragContext}

PARAMETRI UTENTE:
- Livello: ${inputs.level}
- Sesso: ${inputs.gender}
- Frequenza: ${inputs.frequency} giorni/settimana
- Muscoli focus: ${inputs.muscles.join(', ')}
- Note: ${inputs.notes || 'nessuna'}

Rispondi SOLO con JSON valido nel formato:
{"title":"...","description":"...","days":[{"day":"...","label":"...","exercises":[{"id":"...","name":"...","sets":4,"reps":"8-10","rest":"90 sec","notes":""}]}]}`;

  const raw = await callLLM(prompt);
  const content: WorkoutCardContent = JSON.parse(raw);
  for (const day of content.days)
    for (const ex of day.exercises)
      if (!ex.id) ex.id = crypto.randomUUID();

  return NextResponse.json({ content, inputs });
}
```

- [ ] **Step 2: Create `webapp/app/api/cards/route.ts`**
```typescript
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function GET() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { data, error } = await supabase
    .from('workout_cards')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(3);

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data);
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const body = await request.json();

  const { data: existing } = await supabase
    .from('workout_cards')
    .select('id, created_at')
    .eq('user_id', user.id)
    .order('created_at', { ascending: true });

  if (existing && existing.length >= 3) {
    await supabase.from('workout_cards').delete().eq('id', existing[0].id);
  }

  const { data, error } = await supabase
    .from('workout_cards')
    .insert({ user_id: user.id, title: body.content.title, content: body.content, inputs: body.inputs })
    .select()
    .single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data, { status: 201 });
}
```

- [ ] **Step 3: Create `webapp/app/api/cards/[id]/route.ts`**
```typescript
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { content } = await request.json();
  const { data, error } = await supabase
    .from('workout_cards')
    .update({ content, title: content.title })
    .eq('id', id).eq('user_id', user.id)
    .select().single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data);
}

export async function DELETE(
  _: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { error } = await supabase
    .from('workout_cards')
    .delete().eq('id', id).eq('user_id', user.id);

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return new NextResponse(null, { status: 204 });
}
```

- [ ] **Step 4: Create `webapp/app/api/sessions/route.ts`**
```typescript
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import type { WorkoutSession } from '@/lib/types';

export async function GET(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const exercise = new URL(request.url).searchParams.get('exercise');

  const { data, error } = await supabase
    .from('workout_sessions')
    .select('*')
    .eq('user_id', user.id)
    .order('session_date', { ascending: true });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  const result = exercise
    ? (data as WorkoutSession[]).filter(s => s.exercises.some(e => e.name === exercise))
    : data;

  return NextResponse.json(result);
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const body = await request.json();
  const { data, error } = await supabase
    .from('workout_sessions')
    .insert({
      user_id: user.id,
      card_id: body.card_id ?? null,
      exercises: body.exercises,
      notes: body.notes ?? null,
      session_date: body.session_date,
    })
    .select().single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data, { status: 201 });
}
```

- [ ] **Step 5: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/app/api/
git commit -m "feat: API routes — generate, cards, sessions"
```

---

## Task 8: WorkoutCard + ExerciseEditor + ExercisePicker components

**Files:** `webapp/components/WorkoutCard.tsx`, `webapp/components/ExerciseEditor.tsx`, `webapp/components/ExercisePicker.tsx`

- [ ] **Step 1: Create `webapp/components/WorkoutCard.tsx`**
```tsx
'use client';
import Link from 'next/link';
import type { WorkoutCard } from '@/lib/types';

interface Props {
  card: WorkoutCard;
  isActive: boolean;
}

export default function WorkoutCardItem({ card, isActive }: Props) {
  const allExercises = card.content.days.flatMap(d => d.exercises.map(e => e.name));
  const visible = allExercises.slice(0, 4);
  const extra = allExercises.length - visible.length;
  const muscles = card.inputs.muscles.join(' · ');

  return (
    <Link href={`/cards/${card.id}`} style={{ textDecoration: 'none' }}>
      <div className="card" style={{ padding: '1.25rem', opacity: isActive ? 1 : 0.6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
          <span className="overline">{isActive ? 'Attiva' : 'Storico'}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--ink-mute)' }}>
            {new Date(card.created_at).toLocaleDateString('it-IT')}
          </span>
        </div>
        <h3 style={{ margin: '0 0 0.25rem', fontSize: '1.4rem', color: 'var(--ink)' }}>{card.content.title}</h3>
        <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--ink-soft)' }}>
          {card.inputs.level} · {card.inputs.frequency}g/sett · {muscles}
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
          {visible.map(name => (
            <span key={name} className="exercise-chip">{name}</span>
          ))}
          {extra > 0 && <span className="exercise-chip">+{extra} altri</span>}
        </div>
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: Create `webapp/components/ExerciseEditor.tsx`**
```tsx
'use client';
import type { Exercise } from '@/lib/types';

interface Props {
  exercise: Exercise;
  onChange: (ex: Exercise) => void;
  onRemove: () => void;
  onReplace: () => void;
}

export default function ExerciseEditor({ exercise, onChange, onRemove, onReplace }: Props) {
  function update(field: keyof Exercise, value: string | number) {
    onChange({ ...exercise, [field]: value });
  }

  return (
    <div style={{ background: 'var(--surface-2)', borderRadius: 10, padding: '1rem', marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <strong style={{ fontSize: '0.95rem' }}>{exercise.name}</strong>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn-secondary" style={{ padding: '0.3rem 0.7rem', fontSize: '0.8rem' }} onClick={onReplace}>Sostituisci</button>
          <button onClick={onRemove} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', fontSize: '1.1rem' }}>✕</button>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
        {(['sets', 'reps', 'rest'] as const).map(field => (
          <div key={field}>
            <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--ink-mute)', marginBottom: '0.2rem', textTransform: 'uppercase', letterSpacing: '1px' }}>{field}</label>
            <input
              className="input-field"
              style={{ padding: '0.4rem 0.6rem' }}
              value={String(exercise[field])}
              onChange={e => update(field, field === 'sets' ? Number(e.target.value) : e.target.value)}
            />
          </div>
        ))}
      </div>
      <div style={{ marginTop: '0.5rem' }}>
        <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--ink-mute)', marginBottom: '0.2rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Note</label>
        <input className="input-field" style={{ padding: '0.4rem 0.6rem' }} value={exercise.notes} onChange={e => update('notes', e.target.value)} placeholder="Opzionale…" />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `webapp/components/ExercisePicker.tsx`**
```tsx
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
        const names = [...new Set(data.map((r: any) => r.metadata?.name).filter(Boolean))].sort();
        setExercises(names as string[]);
      });
  }, []);

  const filtered = exercises.filter(e => e.toLowerCase().includes(search.toLowerCase()));

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 100, display: 'flex', alignItems: 'flex-end' }}>
      <div style={{ width: '100%', background: 'var(--surface)', borderRadius: '20px 20px 0 0', padding: '1.5rem', maxHeight: '70vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.4rem' }}>Scegli esercizio</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.4rem', cursor: 'pointer' }}>✕</button>
        </div>
        <input className="input-field" placeholder="Cerca…" value={search} onChange={e => setSearch(e.target.value)} style={{ marginBottom: '1rem' }} />
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {filtered.map(name => (
            <button key={name} onClick={() => { onSelect(name); onClose(); }} style={{
              display: 'block', width: '100%', textAlign: 'left', padding: '0.75rem 1rem',
              background: 'none', border: 'none', borderBottom: '1px solid rgba(22,163,74,.1)',
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
```

- [ ] **Step 4: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/components/WorkoutCard.tsx webapp/components/ExerciseEditor.tsx webapp/components/ExercisePicker.tsx
git commit -m "feat: WorkoutCard, ExerciseEditor, ExercisePicker components"
```

---

## Task 9: WorkoutDetail component

**Files:** `webapp/components/WorkoutDetail.tsx`

- [ ] **Step 1: Create `webapp/components/WorkoutDetail.tsx`**
```tsx
'use client';
import { useState } from 'react';
import type { WorkoutCard, WorkoutCardContent, Exercise, WorkoutDay } from '@/lib/types';
import ExerciseEditor from './ExerciseEditor';
import ExercisePicker from './ExercisePicker';

interface Props {
  card: WorkoutCard | { content: WorkoutCardContent; inputs: WorkoutCard['inputs'] };
  mode: 'preview' | 'detail';
  onSave?: (content: WorkoutCardContent) => Promise<void>;
  onSessionLog?: () => void;
  onDownloadPDF?: () => void;
}

export default function WorkoutDetail({ card, mode, onSave, onSessionLog, onDownloadPDF }: Props) {
  const [editing, setEditing] = useState(mode === 'preview');
  const [content, setContent] = useState<WorkoutCardContent>(card.content);
  const [saving, setSaving] = useState(false);
  const [pickerFor, setPickerFor] = useState<{ dayIdx: number; exIdx: number } | null>(null);

  function updateExercise(dayIdx: number, exIdx: number, ex: Exercise) {
    setContent(prev => {
      const days = prev.days.map((d, di) =>
        di === dayIdx
          ? { ...d, exercises: d.exercises.map((e, ei) => (ei === exIdx ? ex : e)) }
          : d
      );
      return { ...prev, days };
    });
  }

  function removeExercise(dayIdx: number, exIdx: number) {
    setContent(prev => ({
      ...prev,
      days: prev.days.map((d, di) =>
        di === dayIdx ? { ...d, exercises: d.exercises.filter((_, ei) => ei !== exIdx) } : d
      ),
    }));
  }

  function addExercise(dayIdx: number, name: string) {
    const newEx: Exercise = { id: crypto.randomUUID(), name, sets: 3, reps: '10', rest: '90 sec', notes: '' };
    setContent(prev => ({
      ...prev,
      days: prev.days.map((d, di) =>
        di === dayIdx ? { ...d, exercises: [...d.exercises, newEx] } : d
      ),
    }));
  }

  function replaceExercise(dayIdx: number, exIdx: number, name: string) {
    const existing = content.days[dayIdx].exercises[exIdx];
    updateExercise(dayIdx, exIdx, { ...existing, name });
  }

  async function handleSave() {
    if (!onSave) return;
    setSaving(true);
    try { await onSave(content); setEditing(false); }
    finally { setSaving(false); }
  }

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '2.2rem', margin: '0 0 0.25rem' }}>{content.title}</h1>
        <p style={{ color: 'var(--ink-soft)', margin: 0 }}>{content.description}</p>
      </div>

      {mode === 'detail' && !editing && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <button className="btn-primary" onClick={() => setEditing(true)}>Modifica scheda</button>
          {onDownloadPDF && <button className="btn-secondary" onClick={onDownloadPDF}>Scarica PDF</button>}
          {onSessionLog && <button className="btn-secondary" onClick={onSessionLog}>Registra sessione</button>}
        </div>
      )}

      {editing && mode === 'detail' && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Salvataggio…' : 'Salva modifiche'}
          </button>
          <button className="btn-secondary" onClick={() => { setContent(card.content); setEditing(false); }}>Annulla</button>
        </div>
      )}

      {content.days.map((day, dayIdx) => (
        <div key={dayIdx} style={{ marginBottom: '2rem' }}>
          <div style={{ marginBottom: '1rem' }}>
            <span className="overline">{day.day}</span>
            <h2 style={{ margin: '0.2rem 0 0', fontSize: '1.3rem' }}>{day.label}</h2>
          </div>

          {editing ? (
            <>
              {day.exercises.map((ex, exIdx) => (
                <ExerciseEditor
                  key={ex.id}
                  exercise={ex}
                  onChange={e => updateExercise(dayIdx, exIdx, e)}
                  onRemove={() => removeExercise(dayIdx, exIdx)}
                  onReplace={() => setPickerFor({ dayIdx, exIdx })}
                />
              ))}
              <button
                className="btn-secondary"
                style={{ width: '100%', marginTop: '0.5rem' }}
                onClick={() => setPickerFor({ dayIdx, exIdx: day.exercises.length })}
              >
                + Aggiungi esercizio
              </button>
            </>
          ) : (
            day.exercises.map(ex => (
              <div key={ex.id} className="card" style={{ padding: '1rem', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '1rem' }}>{ex.name}</strong>
                  <span style={{ fontSize: '0.85rem', color: 'var(--ink-soft)' }}>
                    {ex.sets}×{ex.reps} · {ex.rest}
                  </span>
                </div>
                {ex.notes && <p style={{ margin: '0.4rem 0 0', fontSize: '0.8rem', color: 'var(--ink-mute)' }}>{ex.notes}</p>}
              </div>
            ))
          )}
        </div>
      ))}

      {pickerFor !== null && (
        <ExercisePicker
          onSelect={name => {
            const { dayIdx, exIdx } = pickerFor!;
            if (exIdx < content.days[dayIdx].exercises.length) {
              replaceExercise(dayIdx, exIdx, name);
            } else {
              addExercise(dayIdx, name);
            }
          }}
          onClose={() => setPickerFor(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/components/WorkoutDetail.tsx
git commit -m "feat: WorkoutDetail component with view/edit mode"
```

---

## Task 10: /cards page

**Files:** `webapp/app/cards/page.tsx`

- [ ] **Step 1: Create `webapp/app/cards/page.tsx`**
```tsx
import { createClient } from '@/lib/supabase/server';
import Link from 'next/link';
import WorkoutCardItem from '@/components/WorkoutCard';
import type { WorkoutCard } from '@/lib/types';

export default async function CardsPage() {
  const supabase = await createClient();
  const { data: cards } = await supabase
    .from('workout_cards')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(3);

  const typedCards = (cards ?? []) as WorkoutCard[];

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '2rem' }}>Le mie schede</h1>
        <Link href="/generate">
          <button className="btn-primary" style={{ padding: '0.6rem 1.2rem' }}>+ Nuova scheda</button>
        </Link>
      </div>

      {typedCards.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--ink-soft)', marginBottom: '1rem' }}>Nessuna scheda ancora.</p>
          <Link href="/generate">
            <button className="btn-primary">Crea la tua prima scheda</button>
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {typedCards.map((card, idx) => (
            <WorkoutCardItem key={card.id} card={card} isActive={idx === 0} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/app/cards/page.tsx
git commit -m "feat: /cards page"
```

---

## Task 11: PDF util + /cards/[id] page + SessionModal

**Files:** `webapp/lib/pdf.ts`, `webapp/components/SessionModal.tsx`, `webapp/app/cards/[id]/page.tsx`

- [ ] **Step 1: Create `webapp/lib/pdf.ts`**
```typescript
import type { WorkoutCard } from './types';

export async function generatePDF(card: WorkoutCard): Promise<void> {
  const { jsPDF } = await import('jspdf');
  const doc = new jsPDF();
  let y = 20;

  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text(card.content.title, 20, y);
  y += 10;

  doc.setFontSize(11);
  doc.setFont('helvetica', 'normal');
  doc.text(card.content.description, 20, y, { maxWidth: 170 });
  y += 15;

  for (const day of card.content.days) {
    if (y > 260) { doc.addPage(); y = 20; }
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text(`${day.day} — ${day.label}`, 20, y);
    y += 8;

    for (const ex of day.exercises) {
      if (y > 270) { doc.addPage(); y = 20; }
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.text(`• ${ex.name}  ${ex.sets}×${ex.reps}  rest: ${ex.rest}`, 25, y);
      y += 6;
      if (ex.notes) {
        doc.setTextColor(120);
        doc.text(`  ${ex.notes}`, 25, y);
        doc.setTextColor(0);
        y += 5;
      }
    }
    y += 5;
  }

  doc.save(`${card.content.title.replace(/\s+/g, '_')}.pdf`);
}
```

- [ ] **Step 2: Create `webapp/components/SessionModal.tsx`**
```tsx
'use client';
import { useState } from 'react';
import type { WorkoutCard, SessionExercise, SessionSet } from '@/lib/types';

interface Props {
  card: WorkoutCard;
  onClose: () => void;
}

export default function SessionModal({ card, onClose }: Props) {
  const allExercises = card.content.days.flatMap(d => d.exercises);
  const [exercises, setExercises] = useState<SessionExercise[]>(
    allExercises.map(ex => ({
      name: ex.name,
      sets: Array.from({ length: ex.sets }, () => ({ weight: 0, reps: 0 })),
    }))
  );
  const [notes, setNotes] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [saving, setSaving] = useState(false);

  function updateSet(exIdx: number, setIdx: number, field: keyof SessionSet, value: number) {
    setExercises(prev => prev.map((ex, i) =>
      i === exIdx
        ? { ...ex, sets: ex.sets.map((s, j) => j === setIdx ? { ...s, [field]: value } : s) }
        : ex
    ));
  }

  async function handleSubmit() {
    setSaving(true);
    try {
      await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card_id: card.id, exercises, notes, session_date: date }),
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 100, overflowY: 'auto' }}>
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '2rem 1rem' }}>
        <div style={{ background: 'var(--surface)', borderRadius: 16, padding: '1.5rem', width: '100%', maxWidth: 560 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.5rem' }}>Registra sessione</h2>
            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.4rem', cursor: 'pointer' }}>✕</button>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--ink-soft)' }}>Data</label>
            <input className="input-field" type="date" value={date} onChange={e => setDate(e.target.value)} />
          </div>

          {exercises.map((ex, exIdx) => (
            <div key={exIdx} style={{ marginBottom: '1.25rem' }}>
              <p style={{ margin: '0 0 0.5rem', fontWeight: 600 }}>{ex.name}</p>
              {ex.sets.map((s, setIdx) => (
                <div key={setIdx} style={{ display: 'grid', gridTemplateColumns: 'auto 1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--ink-mute)' }}>Set {setIdx + 1}</span>
                  <div>
                    <input className="input-field" style={{ padding: '0.4rem 0.6rem' }} type="number" placeholder="kg" value={s.weight || ''} onChange={e => updateSet(exIdx, setIdx, 'weight', Number(e.target.value))} />
                  </div>
                  <div>
                    <input className="input-field" style={{ padding: '0.4rem 0.6rem' }} type="number" placeholder="reps" value={s.reps || ''} onChange={e => updateSet(exIdx, setIdx, 'reps', Number(e.target.value))} />
                  </div>
                </div>
              ))}
            </div>
          ))}

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--ink-soft)' }}>Note sessione</label>
            <textarea className="input-field" rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Come è andata?" />
          </div>

          <button className="btn-primary" style={{ width: '100%' }} onClick={handleSubmit} disabled={saving}>
            {saving ? 'Salvataggio…' : 'Salva sessione'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `webapp/app/cards/[id]/page.tsx`**
```tsx
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
        if (found) setCard(found); else router.push('/cards');
      });
  }, [id]);

  if (!card) return <div style={{ padding: '2rem', textAlign: 'center' }}>Caricamento…</div>;

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
      <button onClick={() => router.push('/cards')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--green)', marginBottom: '1rem', fontSize: '0.9rem' }}>
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
```

- [ ] **Step 4: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/lib/pdf.ts webapp/components/SessionModal.tsx webapp/app/cards/
git commit -m "feat: PDF export, SessionModal, /cards/[id] page"
```

---

## Task 12: GenerateWizard + /generate page

**Files:** `webapp/components/GenerateWizard.tsx`, `webapp/app/generate/page.tsx`

- [ ] **Step 1: Create `webapp/components/GenerateWizard.tsx`**
```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { WorkoutInputs, WorkoutCardContent } from '@/lib/types';
import WorkoutDetail from './WorkoutDetail';

const MUSCLES = ['Petto', 'Schiena', 'Quadricipiti', 'Femorali', 'Glutei', 'Spalle', 'Bicipiti', 'Tricipiti', 'Full Body'];

type Step = 1 | 2 | 3 | 4 | 5;
type GenState = 'idle' | 'loading' | 'preview';

const LOADING_MESSAGES = [
  'Analizzo i tuoi parametri…',
  'Cerco gli esercizi migliori…',
  'Costruisco la scheda…',
];

export default function GenerateWizard() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [inputs, setInputs] = useState<WorkoutInputs>({
    level: 'intermedio',
    gender: 'uomo',
    frequency: 3,
    muscles: [],
    notes: '',
  });
  const [genState, setGenState] = useState<GenState>('idle');
  const [loadingMsg, setLoadingMsg] = useState(0);
  const [preview, setPreview] = useState<{ content: WorkoutCardContent; inputs: WorkoutInputs } | null>(null);
  const [saving, setSaving] = useState(false);

  async function generate() {
    setGenState('loading');
    let msgIdx = 0;
    setLoadingMsg(0);
    const interval = setInterval(() => {
      msgIdx = Math.min(msgIdx + 1, LOADING_MESSAGES.length - 1);
      setLoadingMsg(msgIdx);
    }, 1800);

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(inputs),
      });
      const data = await res.json();
      setPreview(data);
      setGenState('preview');
    } catch {
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
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚡</div>
        <p style={{ fontSize: '1.2rem', color: 'var(--ink-soft)' }}>{LOADING_MESSAGES[loadingMsg]}</p>
      </div>
    );
  }

  if (genState === 'preview' && preview) {
    return (
      <div>
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <button className="btn-primary" onClick={saveCard} disabled={saving}>
            {saving ? 'Salvataggio…' : 'Salva scheda'}
          </button>
          <button className="btn-secondary" onClick={generate}>Rigenera</button>
        </div>
        <WorkoutDetail card={{ content: preview.content, inputs: preview.inputs } as any} mode="preview" />
      </div>
    );
  }

  const progress = (step / 5) * 100;

  return (
    <div style={{ maxWidth: 520, margin: '0 auto' }}>
      <div style={{ height: 4, background: 'rgba(22,163,74,.15)', borderRadius: 2, marginBottom: '2rem' }}>
        <div style={{ height: '100%', width: `${progress}%`, background: 'var(--green)', borderRadius: 2, transition: 'width 0.3s' }} />
      </div>

      {step === 1 && (
        <StepSection title="Livello" subtitle="Qual è la tua esperienza?">
          {(['principiante', 'intermedio', 'avanzato'] as const).map(l => (
            <button key={l} className={`pill ${inputs.level === l ? 'on' : ''}`} onClick={() => setInputs(p => ({ ...p, level: l }))}
              style={{ marginRight: '0.5rem', marginBottom: '0.5rem', textTransform: 'capitalize' }}>
              {l}
            </button>
          ))}
        </StepSection>
      )}

      {step === 2 && (
        <StepSection title="Sesso" subtitle="Come ti identifichi?">
          {(['uomo', 'donna'] as const).map(g => (
            <button key={g} className={`pill ${inputs.gender === g ? 'on' : ''}`} onClick={() => setInputs(p => ({ ...p, gender: g }))}
              style={{ marginRight: '0.5rem', textTransform: 'capitalize' }}>
              {g}
            </button>
          ))}
        </StepSection>
      )}

      {step === 3 && (
        <StepSection title="Frequenza" subtitle="Quanti giorni ti alleni a settimana?">
          {[2, 3, 4, 5].map(f => (
            <button key={f} className={`pill ${inputs.frequency === f ? 'on' : ''}`} onClick={() => setInputs(p => ({ ...p, frequency: f }))}
              style={{ marginRight: '0.5rem' }}>
              {f === 5 ? '5+ giorni' : `${f} giorni`}
            </button>
          ))}
        </StepSection>
      )}

      {step === 4 && (
        <StepSection title="Muscoli focus" subtitle="Seleziona uno o più gruppi muscolari.">
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
        </StepSection>
      )}

      {step === 5 && (
        <StepSection title="Note aggiuntive" subtitle="Hai attrezzatura limitata, infortuni, preferenze?">
          <textarea
            className="input-field"
            rows={4}
            placeholder="Es. no bilanciere, solo manubri, palestra casa…"
            value={inputs.notes}
            onChange={e => setInputs(p => ({ ...p, notes: e.target.value }))}
          />
        </StepSection>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem' }}>
        {step > 1
          ? <button className="btn-secondary" onClick={() => setStep(s => (s - 1) as Step)}>Indietro</button>
          : <span />
        }
        {step < 5
          ? <button className="btn-primary" onClick={() => setStep(s => (s + 1) as Step)} disabled={step === 4 && inputs.muscles.length === 0}>
              Avanti
            </button>
          : <button className="btn-primary" onClick={generate}>Genera scheda ⚡</button>
        }
      </div>
    </div>
  );
}

function StepSection({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="overline">Step</span>
      <h2 style={{ margin: '0.25rem 0 0.5rem', fontSize: '1.8rem' }}>{title}</h2>
      <p style={{ color: 'var(--ink-soft)', marginBottom: '1.5rem' }}>{subtitle}</p>
      <div>{children}</div>
    </div>
  );
}
```

- [ ] **Step 2: Create `webapp/app/generate/page.tsx`**
```tsx
import GenerateWizard from '@/components/GenerateWizard';

export default function GeneratePage() {
  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Nuova scheda</h1>
      <p style={{ color: 'var(--ink-soft)', marginBottom: '2rem' }}>Rispondi a 5 domande e l'AI crea la tua scheda personalizzata.</p>
      <GenerateWizard />
    </div>
  );
}
```

- [ ] **Step 3: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/components/GenerateWizard.tsx webapp/app/generate/page.tsx
git commit -m "feat: GenerateWizard 5-step + /generate page"
```

---

## Task 13: PerformanceChart + /track + /settings pages

**Files:** `webapp/components/PerformanceChart.tsx`, `webapp/app/track/page.tsx`, `webapp/app/settings/page.tsx`

- [ ] **Step 1: Create `webapp/components/PerformanceChart.tsx`**
```tsx
'use client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { WorkoutSession } from '@/lib/types';

interface Props {
  sessions: WorkoutSession[];
  exercise: string;
}

export default function PerformanceChart({ sessions, exercise }: Props) {
  const data = sessions
    .filter(s => s.exercises.some(e => e.name === exercise))
    .map(s => {
      const ex = s.exercises.find(e => e.name === exercise)!;
      const maxWeight = Math.max(...ex.sets.map(set => set.weight));
      return { date: s.session_date, weight: maxWeight };
    });

  if (data.length === 0) return <p style={{ color: 'var(--ink-mute)', textAlign: 'center', padding: '2rem' }}>Nessun dato ancora.</p>;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(22,163,74,.1)" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--ink-mute)' }} />
        <YAxis tick={{ fontSize: 11, fill: 'var(--ink-mute)' }} unit=" kg" />
        <Tooltip
          formatter={(v: number) => [`${v} kg`, 'Peso max']}
          contentStyle={{ background: 'var(--surface)', border: '1px solid rgba(22,163,74,.2)', borderRadius: 8 }}
        />
        <Bar dataKey="weight" fill="var(--green)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Create `webapp/app/track/page.tsx`**
```tsx
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

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return;
      supabase.from('user_settings').select('*').eq('user_id', user.id).single()
        .then(({ data }) => setSettings(data));
    });
    fetch('/api/sessions').then(r => r.json()).then((data: WorkoutSession[]) => {
      setSessions(data ?? []);
      const names = [...new Set((data ?? []).flatMap(s => s.exercises.map(e => e.name)))].sort();
      setExercises(names);
      if (names.length > 0) setSelected(names[0]);
      setLoading(false);
    });
  }, []);

  async function enableTracking() {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;
    await supabase.from('user_settings').upsert({ user_id: user.id, tracking_enabled: true });
    setSettings(prev => ({ ...(prev ?? { user_id: user.id, updated_at: '' }), tracking_enabled: true }));
  }

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Caricamento…</div>;

  if (!settings?.tracking_enabled) {
    return (
      <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>Performance tracking</h1>
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--ink-soft)', marginBottom: '1.5rem' }}>Abilita il tracking per visualizzare i tuoi progressi nel tempo.</p>
          <button className="btn-primary" onClick={enableTracking}>Abilita tracking</button>
        </div>
      </div>
    );
  }

  const now = new Date();
  const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  const selectedSessions = sessions.filter(s => s.exercises.some(e => e.name === selected));
  const recentSessions = selectedSessions.filter(s => s.session_date >= thirtyDaysAgo);

  const allWeights = selectedSessions.flatMap(s =>
    s.exercises.filter(e => e.name === selected).flatMap(e => e.sets.map(set => set.weight))
  );
  const maxWeight = allWeights.length > 0 ? Math.max(...allWeights) : 0;

  const recentWeights = recentSessions.flatMap(s =>
    s.exercises.filter(e => e.name === selected).flatMap(e => e.sets.map(set => set.weight))
  );
  const recentMax = recentWeights.length > 0 ? Math.max(...recentWeights) : 0;
  const olderWeights = selectedSessions
    .filter(s => s.session_date < thirtyDaysAgo)
    .flatMap(s => s.exercises.filter(e => e.name === selected).flatMap(e => e.sets.map(set => set.weight)));
  const olderMax = olderWeights.length > 0 ? Math.max(...olderWeights) : 0;
  const delta = olderMax > 0 ? (((recentMax - olderMax) / olderMax) * 100).toFixed(1) : null;

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '1.5rem' }}>Performance tracking</h1>

      {exercises.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--ink-soft)' }}>Nessuna sessione registrata ancora. Vai su una scheda e premi "Registra sessione".</p>
        </div>
      ) : (
        <>
          <select className="input-field" style={{ maxWidth: 300, marginBottom: '1.5rem' }} value={selected} onChange={e => setSelected(e.target.value)}>
            {exercises.map(name => <option key={name} value={name}>{name}</option>)}
          </select>

          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            {delta !== null && (
              <div className="card" style={{ padding: '1rem 1.5rem', flex: 1 }}>
                <span className="overline">Ultimi 30gg</span>
                <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem', color: Number(delta) >= 0 ? 'var(--green)' : '#dc2626' }}>
                  {Number(delta) >= 0 ? '+' : ''}{delta}%
                </p>
              </div>
            )}
            <div className="card" style={{ padding: '1rem 1.5rem', flex: 1 }}>
              <span className="overline">Massimo assoluto</span>
              <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem' }}>{maxWeight} kg</p>
            </div>
            <div className="card" style={{ padding: '1rem 1.5rem', flex: 1 }}>
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
```

- [ ] **Step 3: Create `webapp/app/settings/page.tsx`**
```tsx
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
          <p style={{ margin: 0, fontWeight: 600 }}>Performance tracking</p>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--ink-mute)' }}>Registra i progressi per esercizio</p>
        </div>
        <button
          onClick={toggleTracking}
          style={{
            width: 52, height: 28, borderRadius: 14, border: 'none', cursor: 'pointer',
            background: settings?.tracking_enabled ? 'var(--green)' : 'rgba(22,163,74,.2)',
            position: 'relative', transition: 'background 0.2s',
          }}
        >
          <span style={{
            position: 'absolute', top: 3, left: settings?.tracking_enabled ? 26 : 3,
            width: 22, height: 22, borderRadius: '50%', background: '#fff',
            transition: 'left 0.2s', display: 'block',
          }} />
        </button>
      </div>

      <button className="btn-secondary" style={{ width: '100%', marginTop: '1rem' }} onClick={handleLogout}>
        Logout
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Type-check + commit**
```bash
cd webapp && npx tsc --noEmit
git add webapp/components/PerformanceChart.tsx webapp/app/track/page.tsx webapp/app/settings/page.tsx
git commit -m "feat: PerformanceChart, /track, /settings pages"
```

---

## Task 14: Final check — dev server smoke test

- [ ] **Step 1: Start dev server**
```bash
cd webapp && npm run dev
```

- [ ] **Step 2: Smoke test in browser**

Test these flows:
1. Open http://localhost:3000 → see auth page
2. Register new user → redirected to /cards
3. Click "Nuova scheda" → /generate wizard loads
4. Complete all 5 steps → loading screen → preview generated card
5. Save card → redirected to /cards/[id]
6. Test edit mode: modify an exercise, save
7. Test download PDF
8. Register a session → modal opens, submit
9. /track → enable tracking, verify chart appears (if sessions exist)
10. /settings → toggle tracking, logout

- [ ] **Step 3: Fix any runtime errors found**

- [ ] **Step 4: Final commit**
```bash
cd webapp && git add . && git commit -m "feat: complete Prime frontend webapp"
```

---

## Checklist finale

- [ ] All 6 pages render without errors
- [ ] Auth redirect works (unauthenticated → /, authenticated on / → /cards)
- [ ] Generate wizard calls API and shows preview
- [ ] Card save respects 3-card limit (oldest deleted)
- [ ] Inline edit saves to Supabase
- [ ] PDF download works
- [ ] Session modal saves to DB
- [ ] Performance chart shows data after tracking enabled
- [ ] `npx tsc --noEmit` passes with 0 errors
