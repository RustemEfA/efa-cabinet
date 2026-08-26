// Supabase-клиент для серверных компонентов и route handlers.
// Читает/пишет сессию через cookies() из next/headers — так авторизация
// переживает переход между страницами без лишнего JS на клиенте.
import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";

export function createClient() {
  const cookieStore = cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value, ...options });
          } catch {
            // set() из серверного компонента (не route handler / server action)
            // может упасть — это ожидаемо, middleware ниже обновит сессию.
          }
        },
        remove(name: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value: "", ...options });
          } catch {
            // см. комментарий выше
          }
        }
      }
    }
  );
}
