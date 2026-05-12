# Prime Frontend — Design Spec
**Date:** 2026-05-12
**Project:** Prime Training Card Generator
**Stack:** Next.js 15 App Router · TypeScript · Tailwind CSS · Supabase · OpenRouter

---

## Obiettivo

Costruire il frontend web dell'app Prime: interfaccia per la generazione di schede di allenamento personalizzate basate su RAG, con anteprima editabile, storico schede, salvataggio PDF e tracking delle performance per esercizio nel tempo.

---

## Stack Tecnico

| Layer | Tecnologia |
|---|---|
| Framework | Next.js 15 App Router (in `webapp/`) |
| Linguaggio | TypeScript |
| Styling | Tailwind CSS v4 |
| Auth + DB | Supabase (progetto già esistente) |
| Embedding / RAG | Supabase RPC `match_documents` |
| LLM generazione | OpenRouter `openai/gpt-oss-120b:free` |
| Grafici | Recharts |
| PDF export | jsPDF |
| Font | Barlow Condensed (display) + DM Sans (corpo) via Google Fonts |

---

## Design System

**Palette CSS variables:**
```css
--bg:           #DCFCE7;   /* sfondo pale green */
--surface:      #ffffff;   /* card/superfici */
--surface-2:    #F0FDF4;   /* chip esercizi */
--ink:          #0F1F14;   /* testo principale */
--ink-soft:     #374151;
--ink-mute:     #9CA3AF;
--green:        #16A34A;   /* accento primario */
--green-mid:    #22C55E;
--green-bright: #4ADE80;
--green-glow:   rgba(22,163,74,0.15);
```

**Tipografia:**
- Display/heading: `Barlow Condensed` 800–900, uppercase, letter-spacing tight
- Overline/label: `Barlow Condensed` 700, uppercase, letter-spacing 2.5px, colore `--green`
- Corpo/UI: `DM Sans` 400–600

**Componenti base:**
- Card: `border-radius 14px`, `box-shadow 0 4px 16px rgba(15,31,20,.10)`, hover `translateY(-3px)`
- Bottone primario: bg `--green`, font Barlow Condensed, `box-shadow var(--shadow-green)`, hover lift
- Input: border `1.5px solid`, focus ring `0 0 0 4px var(--green-glow)`
- Pill selezione: bordo sottile, `border-radius 20px`, stato `.on` → bg `--green` testo bianco
- Chip esercizio: bg `--surface-2`, border `rgba(22,163,74,.2)`, hover → `--green-glow`
- Navbar: `backdrop-filter blur(20px)`, bg `rgba(255,255,255,.85)`, border-top sottile

---

## Schema Database (nuove tabelle Supabase)

```sql
-- Schede generate
create table workout_cards (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users not null,
  title       text not null,
  content     jsonb not null,   -- struttura scheda (vedi sotto)
  inputs      jsonb not null,   -- inputs usati per generarla
  created_at  timestamptz default now()
);

-- Sessioni di allenamento per tracking
create table workout_sessions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references auth.users not null,
  card_id      uuid references workout_cards on delete set null,
  exercises    jsonb not null,  -- [{name, sets:[{weight,reps}]}]
  notes        text,
  session_date date not null default current_date,
  created_at   timestamptz default now()
);

-- Impostazioni utente
create table user_settings (
  user_id          uuid primary key references auth.users,
  tracking_enabled boolean default false,
  updated_at       timestamptz default now()
);
```

**Row Level Security:** ogni tabella ha policy `user_id = auth.uid()`.

**Regola storico schede:** massimo 3 schede per utente. Alla creazione della 4ª, la più vecchia (`created_at` minore) viene eliminata dal server prima dell'insert.

### Struttura JSON `workout_cards.content`

```json
{
  "title": "Scheda Forza A",
  "description": "Focus su petto e tricipiti, 4 sedute settimanali.",
  "days": [
    {
      "day": "Lunedì",
      "label": "Petto + Tricipiti",
      "exercises": [
        {
          "id": "uuid-generato-client",
          "name": "Panca Piana",
          "sets": 4,
          "reps": "6-8",
          "rest": "2 min",
          "notes": ""
        }
      ]
    }
  ]
}
```

### Struttura JSON `workout_cards.inputs`

```json
{
  "level": "intermedio",
  "gender": "uomo",
  "frequency": 4,
  "muscles": ["petto", "tricipiti"],
  "notes": "no bilanciere"
}
```

---

## Routing

| Route | Accesso | Descrizione |
|---|---|---|
| `/` | Pubblico | Home + form login/registrazione |
| `/cards` | Auth | Le mie schede (grid max 3) |
| `/cards/[id]` | Auth | Dettaglio scheda + editing inline + PDF |
| `/generate` | Auth | Wizard 5 step → loading → anteprima |
| `/track` | Auth | Performance tracking per esercizio |
| `/settings` | Auth | Abilita tracking, logout |

**Redirect:** utente non autenticato su route protetta → `/`. Utente autenticato su `/` → `/cards`.

---

## Pagine — Dettaglio

### `/` — Home / Auth

- Logo `PRIME` display font grande
- Tab "Accedi" / "Registrati"
- Form email + password
- Submit → Supabase Auth `signInWithPassword` / `signUp`
- Errori mostrati inline sotto il campo

### `/cards` — Le mie schede

- Titolo sezione + pulsante "Nuova scheda" (link a `/generate`)
- Grid di max 3 card (ordine: più recente prima)
- Ogni card mostra: badge stato (Attiva / storico), titolo, sottotitolo (livello · frequenza · muscoli), chip esercizi (max 4 visibili + "+N altri")
- Click su card → `/cards/[id]`
- Card storico (non attiva) opacity ridotta

### `/cards/[id]` — Dettaglio scheda

**View mode:**
- Header: titolo scheda (Barlow Condensed display), sottotitolo
- Per ogni giorno: heading giorno + etichetta muscoli
- Per ogni esercizio: nome, sets×reps, rest, note — con bottoni modifica inline
- Pulsante "Modifica scheda" → entra in edit mode
- Pulsante "Scarica PDF" → genera jsPDF lato client
- Pulsante "Registra sessione" → apre modal session logging

**Edit mode:**
- Ogni esercizio: campi sets/reps/rest/note diventano input editabili
- Bottone "Sostituisci" per ogni esercizio → dropdown/modal con lista esercizi dal DB (Supabase `document_chunks` con `doc_type = 'exercise'`)
- Bottone "Rimuovi" per ogni esercizio
- Bottone "Aggiungi esercizio" in fondo a ogni giorno → stessa selezione da DB
- Bottone "Salva modifiche" → PATCH `/api/cards/[id]`
- Bottone "Annulla"

**Modal "Registra sessione":**
- Lista esercizi della scheda attiva
- Per ogni esercizio: N righe set (una per set), con input peso (kg) e reps
- Campo note sessione
- Data sessione (default oggi, modificabile)
- Submit → POST `/api/sessions`

### `/generate` — Wizard generazione

5 step con progress bar in cima:

**Step 1 — Livello:**
Pill singola: `Principiante` · `Intermedio` · `Avanzato`

**Step 2 — Sesso:**
Pill singola: `Uomo` · `Donna`

**Step 3 — Frequenza settimanale:**
Pill singola: `2 giorni` · `3 giorni` · `4 giorni` · `5+ giorni`

**Step 4 — Muscoli focus:**
Pill multi-select: `Petto` · `Schiena` · `Quadricipiti` · `Femorali` · `Glutei` · `Spalle` · `Bicipiti` · `Tricipiti` · `Full Body`

**Step 5 — Note aggiuntive:**
Textarea libera, placeholder `"Es. no bilanciere, solo manubri, palestra casa…"` — opzionale

Navigazione: bottoni Avanti / Indietro, validazione minima (step 1-4 richiedono selezione).

**Schermata loading:**
- Messaggio animato: "Analizzo i tuoi parametri…" → "Cerco gli esercizi migliori…" → "Costruisco la scheda…"
- Chiama `POST /api/generate`

**Anteprima generata:**
- Stessa UI di `/cards/[id]` in edit mode
- Bottone "Salva scheda" → `POST /api/cards` + redirect a `/cards/[id]`
- Bottone "Rigenera" → ri-chiama API con stessi input

### `/track` — Performance tracking

- Visibile solo se `user_settings.tracking_enabled = true`; altrimenti mostra banner con toggle per abilitare
- Dropdown o tab per selezionare esercizio
- Stat chip: variazione % ultimi 30gg, massimo assoluto, n° sessioni
- Grafico a barre (Recharts `BarChart`): asse X = date sessioni, asse Y = peso massimo per sessione
- Hover su barra mostra tooltip con peso + reps

### `/settings` — Impostazioni

- Toggle "Abilita performance tracking" → update `user_settings`
- Bottone logout → `supabase.auth.signOut()` + redirect a `/`

---

## API Routes

### `POST /api/generate`

**Input:**
```json
{ "level": "intermedio", "gender": "uomo", "frequency": 4, "muscles": ["petto","tricipiti"], "notes": "no bilanciere" }
```

**Logica:**
1. Chiama `match_documents` RPC su Supabase con embedding della query costruita dagli input (es. `"esercizi petto tricipiti intermedio forza"`)
2. Assembla prompt con i chunk recuperati + inputs utente
3. Chiama OpenRouter `openai/gpt-oss-120b:free` con il prompt — risposta attesa in JSON
4. Parsa e valida JSON risposta
5. Restituisce struttura `WorkoutCard` al client

**Output:** `{ content: WorkoutCardContent, inputs: WorkoutInputs }`

**Prompt template:**
```
Sei un personal trainer esperto. Genera una scheda di allenamento personalizzata in JSON.

CONTESTO DAL DATABASE ESERCIZI E LINEE GUIDA:
{rag_chunks}

PARAMETRI UTENTE:
- Livello: {level}
- Sesso: {gender}
- Frequenza: {frequency} giorni/settimana
- Muscoli focus: {muscles}
- Note: {notes}

Rispondi SOLO con JSON valido nel formato:
{"title":"...","description":"...","days":[{"day":"...","label":"...","exercises":[{"id":"...","name":"...","sets":N,"reps":"...","rest":"...","notes":"..."}]}]}
```

### `GET /api/cards`

Restituisce le schede dell'utente autenticato, ordinate per `created_at DESC`, max 3.

### `POST /api/cards`

Salva nuova scheda. Prima dell'insert: conta schede esistenti → se ≥ 3, elimina la più vecchia.

### `PATCH /api/cards/[id]`

Aggiorna `content` di una scheda esistente (editing inline).

### `DELETE /api/cards/[id]`

Elimina scheda per id.

### `POST /api/sessions`

Salva una sessione di allenamento. Body: `{ card_id, exercises, notes, session_date }`.

### `GET /api/sessions`

Query param: `?exercise=Panca+Piana`. Restituisce sessioni dell'utente filtrate per nome esercizio, ordinate per data.

---

## Autenticazione

Supabase Auth con email + password. Client-side: `@supabase/ssr` con cookie-based session. Middleware Next.js (`middleware.ts`) protegge tutte le route tranne `/`.

---

## Variabili d'ambiente (`.env.local` in `webapp/`)

```
NEXT_PUBLIC_SUPABASE_URL=https://cmtplysufbgslmpygbfz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
SUPABASE_SERVICE_KEY=<service_role_key>
OPENROUTER_LLM_KEY=<sk-or-v1-8204ecc...>
OPENROUTER_LLM_MODEL=openai/gpt-oss-120b:free
OPENROUTER_EMBED_KEY=<sk-or-v1-322680...>
EMBED_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
```

---

## Struttura File `webapp/`

```
webapp/
├── app/
│   ├── layout.tsx              # font Google, CSS vars, Toaster
│   ├── page.tsx                # / — Auth page
│   ├── cards/
│   │   ├── page.tsx            # /cards
│   │   └── [id]/page.tsx       # /cards/[id]
│   ├── generate/
│   │   └── page.tsx            # /generate wizard
│   ├── track/
│   │   └── page.tsx            # /track
│   ├── settings/
│   │   └── page.tsx            # /settings
│   └── api/
│       ├── generate/route.ts
│       ├── cards/
│       │   ├── route.ts        # GET, POST
│       │   └── [id]/route.ts   # PATCH, DELETE
│       └── sessions/
│           └── route.ts        # GET, POST
├── components/
│   ├── AuthForm.tsx
│   ├── WorkoutCard.tsx         # card in lista /cards
│   ├── WorkoutDetail.tsx       # view + edit mode; prop mode:'preview'|'detail'
│   ├── ExerciseEditor.tsx      # riga esercizio editabile
│   ├── ExercisePicker.tsx      # modal selezione esercizio da DB
│   ├── GenerateWizard.tsx      # wizard 5 step
│   ├── SessionModal.tsx        # modal log sessione
│   ├── PerformanceChart.tsx    # Recharts grafico
│   └── Navbar.tsx              # navbar fissa in basso
├── lib/
│   ├── supabase/
│   │   ├── client.ts           # createBrowserClient
│   │   └── server.ts           # createServerClient (API routes)
│   ├── openrouter.ts           # fetch LLM + fetch embed
│   ├── rag.ts                  # buildQuery + callMatchDocuments
│   ├── pdf.ts                  # generatePDF(card) → download
│   └── types.ts                # WorkoutCard, WorkoutDay, Exercise, Session
├── middleware.ts               # protezione route
├── tailwind.config.ts
├── next.config.ts
└── package.json
```

---

## Fuori Scope

- Upload / aggiornamento documenti RAG (già gestito dagli script Python)
- Notifiche push / reminder allenamento
- Condivisione schede tra utenti
- Dark mode
- Internazionalizzazione
