"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { notifyTelegram } from "@/lib/telegram";
import { createYookassaPayment } from "@/lib/yookassa";
import { SCAN_PRICE, INTERVIEW_PRICE } from "@/lib/pricing";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://app.ef-a.ru";

export async function submitScanRequest(formData: FormData) {
  const projectId = String(formData.get("project_id") || "");
  const orgName = String(formData.get("scan-org") || "").trim();
  const site = String(formData.get("scan-site") || "").trim();
  const social = String(formData.get("scan-social") || "").trim();

  if (!projectId || !orgName) return;

  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  await supabase.from("scan_requests").insert({
    project_id: projectId,
    owner_id: user.id,
    org_name: orgName,
    site: site || null,
    social: social || null,
  });

  await notifyTelegram(
    `📋 Новая заявка «Скан репутации»\nОрганизация: ${orgName}\nСайт: ${site || "—"}\nСоцсети: ${social || "—"}`
  );

  revalidatePath(`/dashboard/${projectId}`);
}

export async function submitInterviewRequest(formData: FormData) {
  const projectId = String(formData.get("project_id") || "");
  const contact = String(formData.get("interview-contact") || "").trim();
  const comment = String(formData.get("interview-comment") || "").trim();
  const acceptedOffer = formData.get("interview-offer") === "on";
  const rosterFile = formData.get("interview-roster") as File | null;

  if (!projectId || !contact || !acceptedOffer) return;

  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  let rosterPath = null;
  if (rosterFile && typeof rosterFile === "object" && "size" in rosterFile && rosterFile.size > 0) {
    const ext = (rosterFile.name || "file").split(".").pop() || "bin";
    const path = `${projectId}/roster-${Date.now()}.${ext}`;
    const { error } = await supabase.storage.from("documents").upload(path, rosterFile, {
      contentType: rosterFile.type || undefined,
      upsert: false,
    });
    if (!error) rosterPath = path;
  }

  await supabase.from("interview_requests").insert({
    project_id: projectId,
    owner_id: user.id,
    contact,
    roster_storage_path: rosterPath,
    comment: comment || null,
  });

  await notifyTelegram(
    `🧑‍💼 Новая заявка «Интервью сотрудников» (Шаг 2)\nКонтакт: ${contact}\nШтатное расписание: ${rosterPath ? "приложено" : "не приложено"}\nКомментарий: ${comment || "—"}`
  );

  revalidatePath(`/dashboard/${projectId}`);
}

// ------------------------------------------------------------------
// Онлайн-оплата через ЮKassa
// ------------------------------------------------------------------

// Общая логика для обоих шагов: проверяем, что заявка по этому шагу вообще
// подана и ещё не оплачена (иначе action можно было бы дёрнуть напрямую и
// создать лишний платёж), считаем цену со скидкой партнёра и создаём
// платёж с редиректом на страницу оплаты ЮKassa.
async function createStepPayment(
  formData: FormData,
  orderKind: "scan" | "interview",
  table: string,
  basePrice: number,
  description: string
) {
  const projectId = String(formData.get("project_id") || "");
  if (!projectId) return;

  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  const { data: request } = await supabase
    .from(table)
    .select("id, status")
    .eq("project_id", projectId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!request || request.status === "paid" || request.status === "done") return;

  const { data: profile } = await supabase
    .from("profiles")
    .select("partner_discount_rate")
    .eq("id", user.id)
    .maybeSingle();

  const discountRate = profile?.partner_discount_rate || 0;
  const amount = discountRate ? Math.round(basePrice * (1 - discountRate)) : basePrice;

  const payment = await createYookassaPayment({
    amount,
    description,
    returnUrl: `${SITE_URL}/dashboard/${projectId}?payment=return`,
    metadata: { project_id: projectId, order_kind: orderKind, user_id: user.id },
    // Уникален для каждой попытки оплаты — иначе повторный клик "Оплатить"
    // после отменённого платежа вернёт тот же (уже нерабочий) платёж.
    idempotenceKey: `${projectId}-${orderKind}-${Date.now()}`
  });

  if (payment.confirmation?.confirmation_url) {
    redirect(payment.confirmation.confirmation_url);
  }
}

export async function createScanPayment(formData: FormData) {
  await createStepPayment(formData, "scan", "scan_requests", SCAN_PRICE, "Скан репутации — Эффективная Автоматизация");
}

export async function createInterviewPayment(formData: FormData) {
  await createStepPayment(formData, "interview", "interview_requests", INTERVIEW_PRICE, "Интервью сотрудников — Эффективная Автоматизация");
}
