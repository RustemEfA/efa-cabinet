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
