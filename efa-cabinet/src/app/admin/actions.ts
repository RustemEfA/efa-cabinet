"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminEmail } from "@/lib/admin";
import { SCAN_PRICE, INTERVIEW_PRICE } from "@/lib/pricing";

// Проверяем на КАЖДОМ вызове action, что действие выполняет именно админ —
// не полагаемся только на то, что страница /admin уже проверила доступ,
// потому что server action можно дёрнуть напрямую.
async function assertAdmin() {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!isAdminEmail(user?.email)) {
    throw new Error("Доступ запрещён");
  }
}

function safeFileName(name: string) {
  return name
    .normalize("NFKD")
    .replace(/[^\w.\-]+/g, "_")
    .slice(-120);
}

export async function adminUploadDeliverable(formData: FormData) {
  await assertAdmin();

  const projectId = String(formData.get("project_id") || "");
  const file = formData.get("file") as File | null;
  if (!projectId || !file || file.size === 0) return;

  const admin = createAdminClient();

  const { data: project } = await admin
    .from("projects")
    .select("id, owner_id")
    .eq("id", projectId)
    .single();
  if (!project) return;

  const path = `${project.owner_id}/${projectId}/deliverable-${Date.now()}-${safeFileName(file.name)}`;

  const { error: uploadError } = await admin.storage
    .from("documents")
    .upload(path, file, { contentType: file.type || undefined, upsert: false });
  if (uploadError) return;

  await admin.from("documents").insert({
    project_id: projectId,
    owner_id: project.owner_id,
    storage_path: path,
    file_name: file.name,
    file_size: file.size,
    kind: "deliverable"
  });

  revalidatePath(`/admin/${projectId}`);
  revalidatePath(`/dashboard/${projectId}`);
}

export async function adminDeleteDeliverable(formData: FormData) {
  await assertAdmin();

  const documentId = String(formData.get("document_id") || "");
  const storagePath = String(formData.get("storage_path") || "");
  const projectId = String(formData.get("project_id") || "");
  if (!documentId) return;

  const admin = createAdminClient();

  if (storagePath) {
    await admin.storage.from("documents").remove([storagePath]);
  }
  await admin.from("documents").delete().eq("id", documentId);

  revalidatePath(`/admin/${projectId}`);
  revalidatePath(`/dashboard/${projectId}`);
}

// ------------------------------------------------------------------
// Партнёрская программа
// ------------------------------------------------------------------

const ORDER_PRICES: Record<string, number> = {
  scan: SCAN_PRICE,
  interview: INTERVIEW_PRICE
};

const ORDER_TABLE: Record<string, string> = {
  scan: "scan_requests",
  interview: "interview_requests"
};

// Отмечает оплату конкретного шага (Скан / Интервью) клиентом. Если у
// клиента есть привязанный партнёр — автоматически создаёт/обновляет
// строку начисления в partner_orders.
export async function adminMarkPaid(formData: FormData) {
  await assertAdmin();

  const projectId = String(formData.get("project_id") || "");
  const orderKind = String(formData.get("order_kind") || "");
  const amount = Number(String(formData.get("amount") || "").replace(",", "."));

  if (!projectId || !ORDER_PRICES[orderKind] || !amount || amount <= 0) return;

  const admin = createAdminClient();
  const table = ORDER_TABLE[orderKind];

  await admin.from(table).update({ status: "paid" }).eq("project_id", projectId);

  const { data: project } = await admin
    .from("projects")
    .select("id, owner_id")
    .eq("id", projectId)
    .single();
  if (!project) return;

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

  revalidatePath(`/admin/${projectId}`);
  revalidatePath("/admin/partners");
  revalidatePath(`/dashboard/${projectId}`);
}

export async function adminCreatePartner(formData: FormData) {
  await assertAdmin();

  const fullName = String(formData.get("full_name") || "").trim();
  const email = String(formData.get("email") || "").trim().toLowerCase();
  const phone = String(formData.get("phone") || "").trim();
  const promoCode = String(formData.get("promo_code") || "").trim().toUpperCase();
  const commissionRate = Number(formData.get("commission_rate") || 0.5);
  const discountRate = Number(formData.get("discount_rate") || 0.1);

  if (!fullName || !email || !promoCode) return;

  const admin = createAdminClient();
  await admin.from("partners").insert({
    full_name: fullName,
    email,
    phone: phone || null,
    promo_code: promoCode,
    commission_rate: commissionRate,
    client_discount_rate: discountRate
  });

  revalidatePath("/admin/partners");
}

export async function adminMarkPartnerPayout(formData: FormData) {
  await assertAdmin();

  const orderId = String(formData.get("order_id") || "");
  const partnerId = String(formData.get("partner_id") || "");
  if (!orderId) return;

  const admin = createAdminClient();

  const { data: order } = await admin
    .from("partner_orders")
    .select("commission_amount")
    .eq("id", orderId)
    .single();
  if (!order) return;

  const amountRaw = formData.get("amount");
  const amount = amountRaw ? Number(String(amountRaw).replace(",", ".")) : order.commission_amount;

  await admin
    .from("partner_orders")
    .update({
      commission_status: "paid",
      commission_paid_amount: amount,
      commission_paid_at: new Date().toISOString()
    })
    .eq("id", orderId);

  revalidatePath(`/admin/partners/${partnerId}`);
  revalidatePath("/admin/partners");
}
