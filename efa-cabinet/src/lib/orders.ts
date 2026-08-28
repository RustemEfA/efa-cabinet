import { SCAN_PRICE, INTERVIEW_PRICE } from "@/lib/pricing";

export const ORDER_PRICES: Record<string, number> = {
  scan: SCAN_PRICE,
  interview: INTERVIEW_PRICE
};

export const ORDER_TABLE: Record<string, string> = {
  scan: "scan_requests",
  interview: "interview_requests"
};

// Отмечает шаг (Скан / Интервью) оплаченным и, если у клиента есть
// привязанный партнёр, создаёт/обновляет начисление в partner_orders.
// Общая точка входа и для ручной кнопки "Отметить оплаченным" в админке,
// и для вебхука ЮKassa — чтобы обе ветки считали комиссию партнёра
// одинаково и не расходились логикой.
export async function markOrderPaid(
  admin: any,
  params: { projectId: string; orderKind: string; amount: number }
): Promise<boolean> {
  const { projectId, orderKind, amount } = params;
  if (!projectId || !ORDER_PRICES[orderKind] || !amount || amount <= 0) return false;

  const table = ORDER_TABLE[orderKind];
  await admin.from(table).update({ status: "paid" }).eq("project_id", projectId);

  const { data: project } = await admin
    .from("projects")
    .select("id, owner_id")
    .eq("id", projectId)
    .single();
  if (!project) return true;

  const { data: profile } = await admin
    .from("profiles")
    .select("company_name, contact_name, partner_id")
    .eq("id", project.owner_id)
    .maybeSingle();

  if (profile?.partner_id) {
    const { data: partner } = await admin
      .from("partners")
      .select("id, client_discount_rate, commission_rate")
      .eq("id", profile.partner_id)
      .maybeSingle();

    if (partner) {
      const grossAmount = ORDER_PRICES[orderKind];
      const discountAmount = Math.round(grossAmount * partner.client_discount_rate);
      const commissionAmount = Math.round(amount * partner.commission_rate);
      const clientLabel = profile.company_name || profile.contact_name || "Клиент без названия";

      await admin.from("partner_orders").upsert(
        {
          project_id: projectId,
          partner_id: partner.id,
          order_kind: orderKind,
          client_label: clientLabel,
          gross_amount: grossAmount,
          discount_amount: discountAmount,
          client_paid_amount: amount,
          client_paid_at: new Date().toISOString(),
          commission_amount: commissionAmount,
          commission_status: "accrued"
        },
        { onConflict: "project_id,order_kind" }
      );
    }
  }

  return true;
}
