import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { statusLabel } from "@/lib/statusLabels";
import { submitScanRequest } from "./actions";

export default async function ProjectPage({
  params
}: {
  params: { projectId: string };
}) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: project } = await supabase
    .from("projects")
    .select("id, title, status, created_at")
    .eq("id", params.projectId)
    .single();

  if (!project) notFound();

  const { data: scanRequest } = await supabase
    .from("scan_requests")
    .select("id, org_name, site, social, status, created_at")
    .eq("project_id", project.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const { data: deliverables } = await supabase
    .from("documents")
    .select("id, file_name, storage_path, created_at")
    .eq("project_id", project.id)
    .eq("kind", "deliverable")
    .order("created_at", { ascending: false });

  // Подписанные ссылки на скачивание — бакет приватный, прямых URL нет.
  const deliverablesWithUrls = [];
  for (const doc of deliverables || []) {
    const { data } = await supabase.storage
      .from("documents")
      .createSignedUrl(doc.storage_path, 60 * 60); // 1 час
    deliverablesWithUrls.push({ ...doc, url: data?.signedUrl || null });
  }

  return (
    <>
      <p className="eyebrow"><Link href="/dashboard">← Все проекты</Link></p>
      <div className="card-row" style={{ marginBottom: 4 }}>
        <h1 style={{ marginBottom: 0 }}>{project.title}</h1>
        <span className={`badge ${project.status}`}>{statusLabel(project.status)}</span>
      </div>
      <p className="lead">Создан {new Date(project.created_at).toLocaleDateString("ru-RU")}</p>

      <div className="step-card" style={{ marginTop: 24 }}>
        <div className="step-head">
          <div className="step-num">1</div>
          <h2>Скан репутации</h2>
        </div>

        {scanRequest ? (
          <>
            <p>
              Заявка получена {new Date(scanRequest.created_at).toLocaleDateString("ru-RU")}.
              Мы свяжемся с вами, чтобы принять оплату 990 ₽ и подготовить отчёт — обычно
              это занимает до 2 дней.
            </p>
            <div className="doc-row">
              <span>Организация</span>
              <span className="doc-meta">{scanRequest.org_name}</span>
            </div>
            <div className="doc-row">
              <span>Сайт</span>
              <span className="doc-meta">{scanRequest.site || "—"}</span>
            </div>
            <div className="doc-row">
              <span>Соцсети</span>
              <span className="doc-meta">{scanRequest.social || "—"}</span>
            </div>
          </>
        ) : (
          <>
            <p>
              Заполните три поля — этого достаточно, чтобы собрать отчёт о том, как ваша
              компания выглядит со стороны: юридический профиль, сайт, отзывы на картах
              в сравнении с конкурентами, активность в соцсетях.
            </p>

            <form action={submitScanRequest}>
              <input type="hidden" name="project_id" value={project.id} />

              <label htmlFor="scan-org">Название организации</label>
              <input type="text" id="scan-org" name="scan-org" defaultValue={project.title} required />

              <label htmlFor="scan-site">Сайт организации</label>
              <input type="text" id="scan-site" name="scan-site" placeholder="https://" />

              <label htmlFor="scan-social">Соцсети</label>
              <textarea
                id="scan-social"
                name="scan-social"
                placeholder="Телеграм-канал, Instagram, ВКонтакте, YouTube — ссылки, каждая с новой строки"
              />

              <div className="step-meta">
                <span className="pill">
                  <b>Стоимость:</b>&nbsp;990 ₽
                </span>
                <span className="pill muted">
                  <b>Длительность:</b>&nbsp;до 2 дней
                </span>
              </div>

              <button className="btn" type="submit" style={{ marginTop: 16 }}>
                Отправить заявку
              </button>
            </form>
            <p className="hint">
              Онлайн-оплата подключается — после заявки я свяжусь с вами, чтобы принять
              990 ₽ и подготовить отчёт.
            </p>
          </>
        )}
      </div>

      <p className="hint">
        Не хотите ждать отчёт? <Link href="/dashboard#step-2" style={{ color: "var(--teal)" }}>Перейти к Шагу №2 — Интервью сотрудников →</Link>
      </p>

      <h2 style={{ fontSize: 16, marginTop: 32 }}>Результат</h2>
      {deliverablesWithUrls.length === 0 ? (
        <p className="empty">
          Здесь появится отчёт после того, как мы его подготовим. Мы сообщим вам, когда он будет готов.
        </p>
      ) : (
        deliverablesWithUrls.map((doc) => (
          <div className="doc-row" key={doc.id}>
            <span>{doc.file_name}</span>
            {doc.url ? <a className="btn secondary" style={{ marginTop: 0 }} href={doc.url}>Скачать</a> : null}
          </div>
        ))
      )}
    </>
  );
}
