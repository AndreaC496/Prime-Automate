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
