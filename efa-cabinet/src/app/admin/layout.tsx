import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { isAdminEmail } from "@/lib/admin";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/login?next=/admin");
  if (!isAdminEmail(user.email)) redirect("/dashboard");

  return (
    <>
      <div className="topbar">
        <div className="brand">EfA<span>.</span> Админ-панель</div>
        <div style={{ display: "flex", gap: 12 }}>
          <a href="/admin/partners" className="btn secondary" style={{ marginTop: 0 }}>
            Партнёры
          </a>
          <a href="/dashboard" className="btn secondary" style={{ marginTop: 0 }}>
            В личный кабинет
          </a>
          <form action="/api/logout" method="post">
            <button className="btn secondary" type="submit" style={{ marginTop: 0 }}>
              Выйти
            </button>
          </form>
        </div>
      </div>
      <div className="wrap" style={{ maxWidth: 1100 }}>{children}</div>
    </>
  );
}
