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
