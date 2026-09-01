import { createAdminClient } from "@/lib/supabase/admin";

// Партнёров заводят в /admin/partners только по email/промокоду — без
// привязки к реальному логин-аккаунту (auth_user_id остаётся NULL).
// Кабинет /partner ищет запись по auth_user_id, поэтому без этой связки
// он не находится никогда, даже если человек уже зарегистрировался с тем
// же email. Вызывается при каждом подтверждении почты и при каждом входе:
// как только видим сессию с email, который совпадает с ещё не привязанным
// партнёром — привязываем. Идемпотентно (условие auth_user_id IS NULL).
export async function linkPartnerAccount(userId: string, email?: string | null) {
    if (!userId || !email) return;

  const admin = createAdminClient();
    await admin
      .from("partners")
      .update({ auth_user_id: userId })
      .eq("email", email.toLowerCase())
      .is("auth_user_id", null);
}
