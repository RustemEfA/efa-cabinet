import Link from "next/link";
import { notFound } from "next/navigation";
import { createAdminClient } from "@/lib/supabase/admin";
import { statusLabel } from "@/lib/statusLabels";
import { adminUploadDeliverable, adminDeleteDeliverable, adminMarkPaid } from "../actions";
import { SCAN_PRICE, INTERVIEW_PRICE } from "@/lib/pricing";

export default async function AdminProjectPage({
  params
}: {
  params: { projectId: string };
}) {
  const admin = createAdminClient();

  const { data: project } = await admin
    .from("projects")
    .select("id, title, status, owner_id, created_at")
    .eq("id", params.projectId)
    .single();

  if (!project) notFound();

  const { data: profile } = await admin
    .from("profiles")
    .select("company_name, contact_name, partner_id")
    .eq("id", project.owner_id)
    .maybeSingle();

  const { data: userResp } = await admin.auth.admin.getUserById(project.owner_id);

  let discountRate = 0;
  let partnerLabel: string | null = null;
  if (profile?.partner_id) {
    const { data: partner } = await admin
      .from("partners")
      .select("full_name, promo_code, client_discount_rate")
      .eq("id", profile.partner_id)
      .maybeSingle();
    if (partner) {
      discountRate = partner.client_discount_rate || 0;
      partnerLabel = `${partner.full_name} (${partner.promo_code})`;
    }
  }

  const scanDiscountedPrice = Math.round(SCAN_PRICE * (1 - discountRate));
  const interviewDiscountedPrice = Math.round(INTERVIEW_PRICE * (1 - discountRate));

  const { data: scanRequest } = await admin
    .from("scan_requests")
    .select("id, org_name, site, social, status, created_at")
    .eq("project_id", project.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const { data: interviewRequest } = await admin
    .from("interview_requests")
    .select("id, contact, roster_storage_path, comment, status, created_at")
    .eq("project_id", project.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  let rosterUrl: string | null = null;
  if (interviewRequest?.roster_storage_path) {
    const { data } = await admin.storage
      .from("documents")
      .createSignedUrl(interviewRequest.roster_storage_path, 60 * 60);
    rosterUrl = data?.signedUrl || null;
  }

  const { data: documents } = await admin
    .from("documents")
    .select("id, file_name, storage_path, kind, created_at")
    .eq("project_id", project.id)
    .order("created_at", { ascending: false });

  const documentsWithUrls = [];
  for (const doc of documents || []) {
    const { data } = await admin.storage
      .from("documents")
      .createSignedUrl(doc.storage_path, 60 * 60);
    documentsWithUrls.push({ ...doc, url: data?.signedUrl || null });
  }

  return (
    <>
      <p className="eyebrow">
        <Link href="/admin">← Все проекты</Link>
      </p>
      <div className="card-row" style={{ marginBottom: 4 }}>
        <h1 style={{ marginBottom: 0 }}>{project.title}</h1>
        <span className={`badge ${project.status}`}>{statusLabel(project.status)}</span>
      </div>
      <p className="lead">
        {profile?.company_name || profile?.contact_name || "Клиент"} ·{" "}
        {userResp?.user?.email || "почта неизвестна"} · создан{" "}
        {new Date(project.created_at).toLocaleDateString("ru-RU")}
        {partnerLabel ? (
          <>
            {" "}· пришёл по промокоду партнёра <b>{partnerLabel}</b>
          </>
        ) : null}
      </p>

      <div className="step-card">
        <div className="step-head">
          <div className="step-num">1</div>
          <h2>Скан репутации</h2>
        </div>
        {scanRequest ? (
          <>
            <div className="doc-row"><span>Статус</span><span className="doc-meta">{scanRequest.status}</span></div>
            <div className="doc-row"><span>Организация</span><span className="doc-meta">{scanRequest.org_name}</span></div>
            <div className="doc-row"><span>Сайт</span><span className="doc-meta">{scanRequest.site || "—"}</span></div>
            <div className="doc-row"><span>Соцсети</span><span className="doc-meta">{scanRequest.social || "—"}</span></div>
            <div className="doc-row">
              <span>Заявка от</span>
              <span className="doc-meta">{new Date(scanRequest.created_at).toLocaleString("ru-RU")}</span>
            </div>
            {scanRequest.status !== "paid" && scanRequest.status !== "done" ? (
              <form action={adminMarkPaid} style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "flex-end" }}>
                <input type="hidden" name="project_id" value={project.id} />
                <input type="hidden" name="order_kind" value="scan" />
                <div>
                  <label htmlFor="scan-amount" style={{ fontSize: 12 }}>Сумма оплаты, ₽</label>
                  <input type="number" id="scan-amount" name="amount" defaultValue={scanDiscountedPrice} step="1" min="1" style={{ width: 120 }} />
                </div>
                <button type="submit" className="btn secondary" style={{ marginTop: 0, padding: "6px 12px", fontSize: 12 }}>
                  Отметить оплаченным
                </button>
              </form>
            ) : null}
          </>
        ) : (
          <p className="empty">Заявки ещё нет.</p>
        )}
      </div>

      <div className="step-card">
        <div className="step-head">
          <div className="step-num">2</div>
          <h2>Интервью сотрудников</h2>
        </div>
        {interviewRequest ? (
          <>
            <div className="doc-row"><span>Статус</span><span className="doc-meta">{interviewRequest.status}</span></div>
            <div className="doc-row"><span>Контакт</span><span className="doc-meta">{interviewRequest.contact}</span></div>
            <div className="doc-row">
              <span>Штатное расписание</span>
              {rosterUrl ? (
                <a className="doc-meta" href={rosterUrl}>Скачать</a>
              ) : (
                <span className="doc-meta">не приложено</span>
              )}
            </div>
            <div className="doc-row"><span>Комментарий</span><span className="doc-meta">{interviewRequest.comment || "—"}</span></div>
            <div className="doc-row">
              <span>Заявка от</span>
              <span className="doc-meta">{new Date(interviewRequest.created_at).toLocaleString("ru-RU")}</span>
            </div>
            {interviewRequest.status !== "paid" && interviewRequest.status !== "done" ? (
              <form action={adminMarkPaid} style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "flex-end" }}>
                <input type="hidden" name="project_id" value={project.id} />
                <input type="hidden" name="order_kind" value="interview" />
                <div>
                  <label htmlFor="interview-amount" style={{ fontSize: 12 }}>Сумма оплаты, ₽</label>
                  <input type="number" id="interview-amount" name="amount" defaultValue={interviewDiscountedPrice} step="1" min="1" style={{ width: 120 }} />
                </div>
                <button type="submit" className="btn secondary" style={{ marginTop: 0, padding: "6px 12px", fontSize: 12 }}>
                  Отметить оплаченным
                </button>
              </form>
            ) : null}
          </>
        ) : (
          <p className="empty">Заявки ещё нет.</p>
        )}
      </div>

      <div className="step-card">
        <div className="step-head">
          <div className="step-num">📎</div>
          <h2>Файлы проекта</h2>
        </div>

        {documentsWithUrls.length === 0 ? (
          <p className="empty">Файлов пока нет.</p>
        ) : (
          documentsWithUrls.map((doc) => (
            <div className="doc-row" key={doc.id}>
              <span>
                {doc.file_name} <span className="doc-meta">({doc.kind})</span>
              </span>
              <span style={{ display: "flex", gap: 10, alignItems: "center" }}>
                {doc.url ? <a href={doc.url}>Скачать</a> : null}
                <form action={adminDeleteDeliverable}>
                  <input type="hidden" name="document_id" value={doc.id} />
                  <input type="hidden" name="storage_path" value={doc.storage_path} />
                  <input type="hidden" name="project_id" value={project.id} />
                  <button
                    type="submit"
                    className="btn secondary"
                    style={{ marginTop: 0, padding: "4px 10px", fontSize: 12 }}
                  >
                    Удалить
                  </button>
                </form>
              </span>
            </div>
          ))
        )}

        <form action={adminUploadDeliverable} style={{ marginTop: 16 }}>
          <input type="hidden" name="project_id" value={project.id} />
          <label htmlFor="admin-file">Загрузить результат клиенту</label>
          <input type="file" id="admin-file" name="file" required />
          <button className="btn" type="submit" style={{ marginTop: 12 }}>
            Загрузить
          </button>
        </form>
        <p className="hint">
          Загруженный файл появится у клиента в разделе «Результат» на странице проекта.
        </p>
      </div>
    </>
  );
}
