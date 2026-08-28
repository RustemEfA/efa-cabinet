"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { notifyTelegram } from "@/lib/telegram";

export async function signUp(formData: FormData) {
  const email = String(formData.get("email") || "");
  const password = String(formData.get("password") || "");
  const companyName = String(formData.get("company_name") || "");
  const contactName = String(formData.get("contact_name") || "");
  const promoCode = String(formData.get("promo_code") || "").trim();

  const supabase = createClient();
  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        company_name: companyName,
        contact_name: contactName,
        promo_code: promoCode || null
      },
      emailRedirectTo: `${process.env.NEXT_PUBLIC_SITE_URL}/auth/callback`
    }
  });

  if (error) {
    redirect(`/register?error=${encodeURIComponent(error.message)}`);
  }

  await notifyTelegram(
    `\ud83c\udd95 Новая регистрация в EfA\nEmail: ${email}\nКомпания: ${companyName || "—"}\nИмя: ${contactName || "—"}${promoCode ? `\nПромокод: ${promoCode}` : ""}`
  );

  // Если в Supabase включено подтверждение email (по умолчанию — да),
  // сессии ещё нет: отправляем клиента на страницу "проверьте почту".
  redirect("/register/check-email");
}
