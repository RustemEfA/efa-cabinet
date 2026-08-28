import { createClient } from "@/lib/supabase/server";
import { isAdminEmail } from "@/lib/admin";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const showAdminLink = isAdminEmail(user?.email);

  return (
    <>
      <div className="topbar">
        <div className="brand">EfA<span>.</span> Личный кабинет</div>
        <div style={{ display: "flex", gap: 12 }}>
          {showAdminLink ? (
            <a href="/admin" className="btn secondary" style={{ marginTop: 0 }}>
              Админ
            </a>
          ) : null}
          <form action="/api/logout" method="post">
            <button className="btn secondary" type="submit" style={{ marginTop: 0 }}>
              Выйти
            </button>
          </form>
        </div>
      </div>
      <div className="wrap">{children}</div>
    </>
  );
}
