"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { linkPartnerAccount } from "@/lib/linkPartner";

const AUTH_TIMEOUT_MS = 8000;

function translateAuthError(message: string): string {
    if (message.includes("Invalid login credentials")) {
          return "Неверный email или пароль";
    }
    if (message.includes("Email not confirmed")) {
          return "Email не подтверждён. Проверьте почту.";
    }
    return message;
}

export async function signIn(formData: FormData) {
    const email = String(formData.get("email") || "");
    const password = String(formData.get("password") || "");
    const next = String(formData.get("next") || "/dashboard");

  const supabase = createClient();

  let result: Awaited<ReturnType<typeof supabase.auth.signInWithPassword>>;
    try {
          result = await Promise.race([
                  supabase.auth.signInWithPassword({ email, password }),
                  new Promise<never>((_, reject) =>
                            setTimeout(() => reject(new Error("TIMEOUT")), AUTH_TIMEOUT_MS)
                                           )
                ]);
    } catch (e) {
          redirect(
                  `/login?error=${encodeURIComponent(
                            "Сервис входа сейчас отвечает медленнее обычного (сбой у поставщика авторизации Supabase). Попробуйте ещё раз через минуту."
                          )}&next=${encodeURIComponent(next)}`
                );
          return;
    }

  const { error, data } = result;

  if (error) {
        redirect(`/login?error=${encodeURIComponent(translateAuthError(error.message))}&next=${encodeURIComponent(next)}`);
  }

  if (data.user) {
        await linkPartnerAccount(data.user.id, data.user.email);
  }

  redirect(next || "/dashboard");
}
