import { createClient as base } from '@supabase/supabase-js';

export function createAdminClient() {
  return base(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_KEY!
  );
}
