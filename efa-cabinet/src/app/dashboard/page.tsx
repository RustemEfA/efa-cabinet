import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { createProject } from "./actions";
import { statusLabel } from "@/lib/statusLabels";

export default async function DashboardPage() {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const { data: projects } = await supabase
    .from("projects")
    .select("id, title, status, created_at")
    .order("created_at", { ascending: false });

  return (
    <>
      <p className="eyebrow">Проекты</p>
      <h1>Здравствуйте{user?.user_metadata?.contact_name ? `, ${user.user_metadata.contact_name}` : ""}</h1>
      <p className="lead">
        Заведите проект, загрузите регламенты — дальше мы пришлём ссылку на опрос сотрудников
        и соберём готовую бизнес-архитектуру.
      </p>

      <form action={createProject} style={{ marginBottom: 28 }}>
        <label htmlFor="title">Название нового проекта</label>
        <input type="text" id="title" name="title" placeholder="Например: ООО «Ромашка»" required />
        <button className="btn" type="submit">Создать проект</button>
      </form>

      {!projects || projects.length === 0 ? (
        <p className="empty">Проектов пока нет — создайте первый выше.</p>
      ) : (
        projects.map((p) => (
          <Link key={p.id} href={`/dashboard/${p.id}`} style={{ textDecoration: "none", color: "inherit" }}>
            <div className="card">
              <div className="card-row">
                <div>
                  <p className="card-title">{p.title}</p>
                  <span className={`badge ${p.status}`}>{statusLabel(p.status)}</span>
                </div>
                <span style={{ color: "var(--muted-2)", fontSize: 13 }}>→</span>
              </div>
            </div>
          </Link>
        ))
      )}
    </>
  );
}
