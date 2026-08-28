import Link from "next/link";
import { createAdminClient } from "@/lib/supabase/admin";
import { statusLabel } from "@/lib/statusLabels";

export default async function AdminPage() {
  const admin = createAdminClient();

  const { data: projects } = await admin
    .from("projects")
    .select("id, title, status, owner_id, created_at")
    .order("created_at", { ascending: false });

  const { data: profiles } = await admin
    .from("profiles")
    .select("id, company_name, contact_name");

  const { data: usersResp } = await admin.auth.admin.listUsers({ perPage: 1000 });

  const { data: scanRequests } = await admin
    .from("scan_requests")
    .select("project_id, status");

  const { data: interviewRequests } = await admin
    .from("interview_requests")
    .select("project_id, status");

  const { data: documents } = await admin
    .from("documents")
    .select("project_id, kind");

  const profileById = new Map((profiles || []).map((p) => [p.id, p]));
  const emailById = new Map((usersResp?.users || []).map((u) => [u.id, u.email]));
  const scanByProject = new Map((scanRequests || []).map((r) => [r.project_id, r]));
  const interviewByProject = new Map((interviewRequests || []).map((r) => [r.project_id, r]));

  const deliverableCountByProject = new Map<string, number>();
  for (const d of documents || []) {
    if (d.kind === "deliverable") {
      deliverableCountByProject.set(
        d.project_id,
        (deliverableCountByProject.get(d.project_id) || 0) + 1
      );
    }
  }

  return (
    <>
      <p className="eyebrow">АДМИН-ПАНЕЛЬ</p>
      <h1>Все проекты</h1>
      <p className="lead">
        Здесь — проекты всех клиентов. Открой проект, чтобы загрузить результат,
        скачать файлы от клиента или посмотреть заявки по шагам.
      </p>

      {(projects || []).length === 0 ? (
        <p className="empty">Пока нет ни одного проекта.</p>
      ) : (
        (projects || []).map((p) => {
          const profile = profileById.get(p.owner_id);
          const email = emailById.get(p.owner_id);
          const scan = scanByProject.get(p.id);
          const interview = interviewByProject.get(p.id);
          const deliverables = deliverableCountByProject.get(p.id) || 0;

          return (
            <Link
              key={p.id}
              href={`/admin/${p.id}`}
              className="card"
              style={{ display: "block", textDecoration: "none", color: "inherit" }}
            >
              <div className="card-row">
                <span className="card-title">{p.title}</span>
                <span className={`badge ${p.status}`}>{statusLabel(p.status)}</span>
              </div>
              <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--muted)" }}>
                {profile?.company_name || profile?.contact_name || "Без названия"} ·{" "}
                {email || "почта неизвестна"}
              </p>
              <div className="step-meta" style={{ marginTop: 10 }}>
                <span className="pill muted">Скан: {scan ? scan.status : "нет заявки"}</span>
                <span className="pill muted">
                  Интервью: {interview ? interview.status : "нет заявки"}
                </span>
                <span className="pill muted">Результатов: {deliverables}</span>
              </div>
            </Link>
          );
        })
      )}
    </>
  );
}
