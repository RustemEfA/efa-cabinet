// Supabase-клиент для использования в клиентских компонентах ('use client').
// Работает через анонимный (публичный) ключ — вся защита данных идёт через
// RLS-политики в базе (см. supabase/migrations), а не через секретность ключа.
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
