import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { statusLabel } from "@/lib/statusLabels";
import { submitScanRequest, submitInterviewRequest } from "./actions";

const OFERTA_URL = "/legal/Oferta_i_Specifikatsiya_1_Shag2.pdf";

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

  const { data: interviewRequest } = await supabase
    .from("interview_requests")
    .select("id, contact, roster_storage_path, comment, status, created_at")
    .eq("project_id", project.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  let rosterUrl: string | null = null;
  if (interviewRequest?.roster_storage_path) {
    const { data } = await supabase.storage
      .from("documents")
      .createSignedUrl(interviewRequest.roster_storage_path, 60 * 60);
    rosterUrl = data?.signedUrl || null;
  }

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

      <div className="step-card" id="step-2" style={{ scrollMarginTop: 24 }}>
        <div className="step-head">
          <div className="step-num">2</div>
          <h2>Интервью сотрудников</h2>
        </div>

        {interviewRequest ? (
          <>
            <p>
              Заявка получена {new Date(interviewRequest.created_at).toLocaleDateString("ru-RU")}.
              Мы свяжемся с вами по указанному контакту, чтобы подтвердить детали, получить
              штатное расписание (если не приложено) и запустить интервью сотрудников —
              обычно это занимает около недели.
            </p>
            <div className="doc-row">
              <span>Контакт для связи</span>
              <span className="doc-meta">{interviewRequest.contact}</span>
            </div>
            <div className="doc-row">
              <span>Штатное расписание</span>
              {rosterUrl ? (
                <a className="doc-meta" href={rosterUrl}>Скачать файл</a>
              ) : (
                <span className="doc-meta">не приложено</span>
              )}
            </div>
            <div className="doc-row">
              <span>Комментарий</span>
              <span className="doc-meta">{interviewRequest.comment || "не указан"}</span>
            </div>
            <div className="doc-row">
              <span>Условия</span>
              <span className="doc-meta"><a href={OFERTA_URL} target="_blank" rel="noreferrer">Оферта и спецификация (PDF)</a></span>
            </div>
          </>
        ) : (
          <>
            <p>
              Следующий шаг — интервью сотрудников. На каждого сотрудника — 60–100 вопросов,
              подготовленных под вашу компанию. Сотрудники проходят интервью в удобное для себя
              время, без отрыва от работы.
            </p>
            <p>
              Чтобы подготовить персональные вопросы, нам нужно штатное расписание организации.
              Приложите его сейчас — это ускорит запуск; если под рукой нет, можно прислать позже,
              я свяжусь с вами лично.
            </p>

            <form action={submitInterviewRequest}>
              <input type="hidden" name="project_id" value={project.id} />

              <label htmlFor="interview-contact">Контакт для связи (телефон или Telegram)</label>
              <input type="text" id="interview-contact" name="interview-contact" placeholder="+7 900 000-00-00 или @username" required />

              <label htmlFor="interview-roster">Штатное расписание (PDF, DOCX, XLSX)</label>
              <input type="file" id="interview-roster" name="interview-roster" accept=".pdf,.doc,.docx,.xls,.xlsx" />

              <label htmlFor="interview-comment">Комментарий (необязательно)</label>
              <textarea
                id="interview-comment"
                name="interview-comment"
                placeholder="Что-то, что нам стоит знать заранее: структура отделов, особенности, пожелания по срокам"
              />

              <div className="step-meta">
                <span className="pill">
                  <b>Стоимость:</b>&nbsp;10 000 ₽ — независимо от количества сотрудников
                </span>
                <span className="pill muted">
                  <b>Длительность:</b>&nbsp;~1 неделя
                </span>
              </div>

              <p style={{ marginTop: 14, fontSize: 12.5 }}>
                <a href={OFERTA_URL} target="_blank" rel="noreferrer" className="btn secondary" style={{ marginTop: 0, padding: "6px 12px", fontSize: 12 }}>
                  Оферта и спецификация (PDF)
                </a>
              </p>
              <label style={{ display: "flex", alignItems: "flex-start", gap: 8, marginTop: 14, fontSize: 12.5, color: "var(--muted)" }}>
                <input type="checkbox" name="interview-offer" required style={{ width: "auto", marginTop: 2 }} />
                <span>Принимаю условия публичной оферты и спецификации к Шагу 2</span>
              </label>

              <button className="btn" type="submit" style={{ marginTop: 16 }}>
                Начать Шаг 2
              </button>
            </form>
            <p className="hint">
              После заявки я свяжусь с вами по указанному контакту, чтобы подтвердить детали и
              получить штатное расписание (если не приложено), и запустить интервью.
            </p>
          </>
        )}
      </div>

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
