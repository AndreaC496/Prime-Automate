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
    .select()
    .single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data, { status: 201 });
}
