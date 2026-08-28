import Link from "next/link";
import { createAdminClient } from "@/lib/supabase/admin";
import { adminCreatePartner } from "../actions";

export default async function AdminPartnersPage() {
  const admin = createAdminClient();

  const { data: partners } = await admin
    .from("partners")
    .select("id, full_name, email, promo_code, commission_rate, client_discount_rate, status, created_at")
    .order("created_at", { ascending: false });

  const { data: orders } = await admin
    .from("partner_orders")
    .select("partner_id, commission_amount, commission_paid_amount");

  const statsByPartner = new Map<string, { accrued: number; paid: number }>();
  for (const o of orders || []) {
    const s = statsByPartner.get(o.partner_id) || { accrued: 0, paid: 0 };
    s.accrued += o.commission_amount || 0;
    s.paid += o.commission_paid_amount || 0;
    statsByPartner.set(o.partner_id, s);
  }

  return (
    <>
      <p className="eyebrow"><Link href="/admin">← Все проекты</Link></p>
      <h1>Партнёры</h1>
      <p className="lead">
        Промокоды, скидки клиентам и начисления. Оплату конкретного шага отмечай на
        странице проекта — начисление партнёру появится здесь автоматически.
      </p>

      {(partners || []).length === 0 ? (
        <p className="empty">Партнёров пока нет.</p>
      ) : (
        (partners || []).map((p) => {
          const s = statsByPartner.get(p.id) || { accrued: 0, paid: 0 };
          const owed = s.accrued - s.paid;
          return (
            <Link
              key={p.id}
              href={`/admin/partners/${p.id}`}
              className="card"
              style={{ display: "block", textDecoration: "none", color: "inherit" }}
            >
              <div className="card-row">
                <span className="card-title">{p.full_name}</span>
                <span className="badge">{p.promo_code}</span>
              </div>
              <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--muted)" }}>{p.email}</p>
              <div className="step-meta" style={{ marginTop: 10 }}>
                <span className="pill muted">Начислено: {s.accrued.toLocaleString("ru-RU")} ₽</span>
                <span className="pill muted">Выплачено: {s.paid.toLocaleString("ru-RU")} ₽</span>
                <span className="pill">К выплате: {owed.toLocaleString("ru-RU")} ₽</span>
              </div>
            </Link>
          );
        })
      )}

      <div className="step-card" style={{ marginTop: 24 }}>
        <h2 style={{ marginTop: 0 }}>Добавить партнёра</h2>
        <form action={adminCreatePartner}>
          <label htmlFor="full_name">Имя</label>
          <input type="text" id="full_name" name="full_name" required />

          <label htmlFor="email">Email (тем же должен зарегистрироваться сам партнёр)</label>
          <input type="email" id="email" name="email" required />

          <label htmlFor="phone">Телефон (необязательно)</label>
          <input type="text" id="phone" name="phone" />

          <label htmlFor="promo_code">Промокод</label>
          <input type="text" id="promo_code" name="promo_code" required placeholder="Например, ИВАН10" />

          <div className="step-meta">
            <span className="pill muted">Скидка клиенту: 10% (по умолчанию)</span>
            <span className="pill muted">Комиссия партнёру: 50% (по умолчанию)</span>
          </div>
          <input type="hidden" name="commission_rate" value="0.5" />
          <input type="hidden" name="discount_rate" value="0.1" />

          <button className="btn" type="submit" style={{ marginTop: 16 }}>
            Добавить партнёра
          </button>
        </form>
        <p className="hint">
          Ставки по умолчанию 50% / 10% — если нужно другое для конкретного партнёра,
          скажи, добавлю поля в форму. Пока меняются напрямую в Supabase.
        </p>
      </div>
    </>
  );
}
