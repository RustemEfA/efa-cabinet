// Admin-клиент Supabase — работает через service role key и обходит RLS.
// Используется ТОЛЬКО в серверном коде админ-раздела (/admin/*): server
// components и server actions. Никогда не импортировать в 'use client'
// компоненты и не передавать ключ на клиент.
import { createClient as createSupabaseClient } from "@supabase/supabase-js";

export function createAdminClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      auth: {
        persistSession: false,
        autoRefreshToken: false
      }
    }
  );
}
