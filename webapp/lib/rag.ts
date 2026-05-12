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
