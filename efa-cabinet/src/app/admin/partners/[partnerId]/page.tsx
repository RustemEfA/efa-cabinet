import Link from "next/link";
import { notFound } from "next/navigation";
import { createAdminClient } from "@/lib/supabase/admin";
import { adminMarkPartnerPayout } from "../../actions";

const ORDER_LABELS: Record<string, string> = {
  scan: "Шаг 1 — Скан репутации",
  interview: "Шаг 2 — Интервью сотрудников"
};

export default async function AdminPartnerPage({
  params
}: {
  params: { partnerId: string };
}) {
  const admin = createAdminClient();

  const { data: partner } = await admin
    .from("partners")
    .select("id, full_name, email, phone, promo_code, commission_rate, client_discount_rate, status, created_at")
    .eq("id", params.partnerId)
    .single();

  if (!partner) notFound();

  const { data: orders } = await admin
    .from("partner_orders")
    .select(
      "id, project_id, order_kind, client_label, gross_amount, discount_amount, client_paid_amount, client_paid_at, commission_amount, commission_status, commission_paid_amount, commission_paid_at"
    )
    .eq("partner_id", partner.id)
    .order("created_at", { ascending: false });

  const totalAccrued = (orders || []).reduce((sum, o) => sum + (o.commission_amount || 0), 0);
  const totalPaid = (orders || []).reduce((sum, o) => sum + (o.commission_paid_amount || 0), 0);

  return (
    <>
      <p className="eyebrow"><Link href="/admin/partners">← Все партнёры</Link></p>
      <div className="card-row" style={{ marginBottom: 4 }}>
        <h1 style={{ marginBottom: 0 }}>{partner.full_name}</h1>
        <span className="badge">{partner.promo_code}</span>
      </div>
      <p className="lead">
        {partner.email} · {partner.phone || "телефон не указан"} · комиссия{" "}
        {Math.round(partner.commission_rate * 100)}%, скидка клиенту{" "}
        {Math.round(partner.client_discount_rate * 100)}%
      </p>

      <div className="step-meta" style={{ margin: "16px 0" }}>
        <span className="pill muted">Начислено всего: {totalAccrued.toLocaleString("ru-RU")} ₽</span>
        <span className="pill muted">Выплачено всего: {totalPaid.toLocaleString("ru-RU")} ₽</span>
        <span className="pill">К выплате: {(totalAccrued - totalPaid).toLocaleString("ru-RU")} ₽</span>
      </div>

      {(orders || []).length === 0 ? (
        <p className="empty">Начислений пока нет.</p>
      ) : (
        (orders || []).map((o) => (
          <div className="step-card" key={o.id}>
            <div className="card-row">
              <span className="card-title">
                {o.client_label || "Клиент"} — {ORDER_LABELS[o.order_kind] || o.order_kind}
              </span>
              <span className={`badge ${o.commission_status}`}>
                {o.commission_status === "paid" ? "выплачено" : "начислено"}
              </span>
            </div>
            <div className="doc-row"><span>Полная цена</span><span className="doc-meta">{o.gross_amount.toLocaleString("ru-RU")} ₽</span></div>
            <div className="doc-row"><span>Скидка клиенту</span><span className="doc-meta">{o.discount_amount.toLocaleString("ru-RU")} ₽</span></div>
            <div className="doc-row">
              <span>Оплачено клиентом</span>
              <span className="doc-meta">
                {o.client_paid_amount?.toLocaleString("ru-RU") || "—"} ₽
                {o.client_paid_at ? ` · ${new Date(o.client_paid_at).toLocaleDateString("ru-RU")}` : ""}
              </span>
            </div>
            <div className="doc-row"><span>Начислено партнёру</span><span className="doc-meta">{o.commission_amount?.toLocaleString("ru-RU") || "—"} ₽</span></div>

            {o.commission_status === "paid" ? (
              <div className="doc-row">
                <span>Выплачено</span>
                <span className="doc-meta">
                  {o.commission_paid_amount?.toLocaleString("ru-RU")} ₽
                  {o.commission_paid_at ? ` · ${new Date(o.commission_paid_at).toLocaleDateString("ru-RU")}` : ""}
                </span>
              </div>
            ) : (
              <form action={adminMarkPartnerPayout} style={{ marginTop: 12 }}>
                <input type="hidden" name="order_id" value={o.id} />
                <input type="hidden" name="partner_id" value={partner.id} />
                <input type="hidden" name="amount" value={o.commission_amount || 0} />
                <button
                  type="submit"
                  className="btn secondary"
                  style={{ marginTop: 0, padding: "4px 10px", fontSize: 12 }}
                >
                  Отметить выплаченным ({o.commission_amount?.toLocaleString("ru-RU")} ₽)
                </button>
              </form>
            )}
          </div>
        ))
      )}
    </>
  );
}
