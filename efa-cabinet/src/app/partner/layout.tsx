import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

export default async function PartnerLayout({ children }: { children: React.ReactNode }) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/login?next=/partner");

  const admin = createAdminClient();

  // Партнёра сначала заводит Рустем в админке (email + промокод), а входит
  // партнёр позже, обычной регистрацией на тот же email. При первом заходе
  // в /partner привязываем его аккаунт к записи партнёра по email — дальше
  // работает обычная проверка по auth_user_id.
  const { data: existing } = await admin
    .from("partners")
    .select("id")
    .eq("auth_user_id", user.id)
    .maybeSingle();

  if (!existing && user.email) {
    const { data: byEmail } = await admin
      .from("partners")
      .select("id")
      .eq("email", user.email.toLowerCase())
      .is("auth_user_id", null)
      .maybeSingle();

    if (byEmail) {
      await admin.from("partners").update({ auth_user_id: user.id }).eq("id", byEmail.id);
    }
  }

  const { data: partner } = await admin
    .from("partners")
    .select("id")
    .eq("auth_user_id", user.id)
    .maybeSingle();

  if (!partner) {
    return (
      <div className="auth-wrap">
        <p className="eyebrow">Эффективная Автоматизация</p>
        <h1>Кабинет партнёра</h1>
        <p className="lead">
          У этого аккаунта нет доступа к партнёрскому кабинету. Если вы уже партнёр —
          убедитесь, что зарегистрировались на тот email, который передали Рустему.
        </p>
        <a href="/dashboard" className="btn secondary">В личный кабинет</a>
      </div>
    );
  }

  return (
    <>
      <div className="topbar">
        <div className="brand">EfA<span>.</span> Кабинет партнёра</div>
        <form action="/api/logout" method="post">
          <button className="btn secondary" type="submit" style={{ marginTop: 0 }}>
            Выйти
          </button>
        </form>
      </div>
      <div className="wrap">{children}</div>
    </>
  );
}
