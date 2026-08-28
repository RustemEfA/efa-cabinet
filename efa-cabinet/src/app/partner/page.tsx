import { createClient } from "@/lib/supabase/server";

const ORDER_LABELS: Record<string, string> = {
  scan: "Скан репутации",
  interview: "Интервью сотрудников"
};

export default async function PartnerPage() {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: partner } = await supabase
    .from("partners")
    .select("id, full_name, promo_code, commission_rate, client_discount_rate")
    .eq("auth_user_id", user.id)
    .single();

  if (!partner) return null;

  const { data: orders } = await supabase
    .from("partner_orders")
    .select(
      "id, order_kind, client_label, client_paid_amount, client_paid_at, commission_amount, commission_status, commission_paid_amount, commission_paid_at"
    )
    .eq("partner_id", partner.id)
    .order("created_at", { ascending: false });

  const totalAccrued = (orders || []).reduce((sum, o) => sum + (o.commission_amount || 0), 0);
  const totalPaid = (orders || []).reduce((sum, o) => sum + (o.commission_paid_amount || 0), 0);
  const clientsCount = new Set((orders || []).map((o) => o.client_label)).size;

  return (
    <>
      <p className="eyebrow">КАБИНЕТ ПАРТНЁРА</p>
      <h1>{partner.full_name}</h1>
      <p className="lead">
        Ваш промокод — <b>{partner.promo_code}</b>. Клиент вводит его при регистрации и
        получает скидку {Math.round(partner.client_discount_rate * 100)}%, вам начисляется{" "}
        {Math.round(partner.commission_rate * 100)}% от оплаченной суммы.
      </p>

      <div className="step-meta" style={{ margin: "16px 0" }}>
        <span className="pill muted">Клиентов: {clientsCount}</span>
        <span className="pill muted">Начислено всего: {totalAccrued.toLocaleString("ru-RU")} ₽</span>
        <span className="pill muted">Выплачено: {totalPaid.toLocaleString("ru-RU")} ₽</span>
        <span className="pill">К выплате: {(totalAccrued - totalPaid).toLocaleString("ru-RU")} ₽</span>
      </div>

      <h2 style={{ fontSize: 16 }}>Начисления</h2>
      {(orders || []).length === 0 ? (
        <p className="empty">Пока нет ни одной оплаты по вашему промокоду.</p>
      ) : (
        (orders || []).map((o) => (
          <div className="doc-row" key={o.id}>
            <span>
              {o.client_label || "Клиент"} — {ORDER_LABELS[o.order_kind] || o.order_kind}
              <span className="doc-meta" style={{ display: "block" }}>
                Оплачено клиентом: {o.client_paid_amount?.toLocaleString("ru-RU") || "—"} ₽
                {o.client_paid_at ? ` · ${new Date(o.client_paid_at).toLocaleDateString("ru-RU")}` : ""}
              </span>
            </span>
            <span style={{ textAlign: "right" }}>
              <span className={`badge ${o.commission_status}`}>
                {o.commission_status === "paid" ? "выплачено" : "начислено"}
              </span>
              <span className="doc-meta" style={{ display: "block" }}>
                {o.commission_amount?.toLocaleString("ru-RU") || "—"} ₽
                {o.commission_paid_at ? ` · выплачено ${new Date(o.commission_paid_at).toLocaleDateString("ru-RU")}` : ""}
              </span>
            </span>
          </div>
        ))
      )}
    </>
  );
}
