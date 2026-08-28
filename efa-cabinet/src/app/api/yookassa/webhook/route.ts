import { NextResponse } from "next/server";
import { fetchYookassaPayment } from "@/lib/yookassa";
import { createAdminClient } from "@/lib/supabase/admin";
import { markOrderPaid } from "@/lib/orders";

// URL для настройки в ЛК ЮKassa: Настройки -> HTTP-уведомления ->
// https://app.ef-a.ru/api/yookassa/webhook
//
// ЮKassa не подписывает уведомления криптографически, поэтому телу
// запроса не доверяем — из него берём только id платежа и сразу
// перезапрашиваем его актуальный статус в API ЮKassa своим секретным
// ключом. Только так подтверждённый статус используется для отметки
// заказа оплаченным.
export async function POST(req: Request) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false }, { status: 400 });
  }

  const paymentId = body?.object?.id;
  if (!paymentId) {
    return NextResponse.json({ ok: true });
  }

  let payment;
  try {
    payment = await fetchYookassaPayment(paymentId);
  } catch (e) {
    console.error("yookassa webhook: fetch payment failed", e);
    return NextResponse.json({ ok: false }, { status: 500 });
  }

  if (payment.status !== "succeeded") {
    return NextResponse.json({ ok: true });
  }

  const metadata = payment.metadata || {};
  const projectId = metadata.project_id;
  const orderKind = metadata.order_kind;
  const amount = Number(payment.amount?.value || 0);

  if (!projectId || !orderKind || !amount) {
    return NextResponse.json({ ok: true });
  }

  try {
    const admin = createAdminClient();
    await markOrderPaid(admin, { projectId, orderKind, amount });
  } catch (e) {
    console.error("yookassa webhook: markOrderPaid failed", e);
    return NextResponse.json({ ok: false }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
