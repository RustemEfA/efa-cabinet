"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { notifyTelegram } from "@/lib/telegram";

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
    `\ud83d\udccb Новая заявка «Скан репутации»\nОрганизация: ${orgName}\nСайт: ${site || "—"}\nСоцсети: ${social || "—"}`
  );

  revalidatePath(`/dashboard/${projectId}`);
}
