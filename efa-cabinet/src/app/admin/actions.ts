"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminEmail } from "@/lib/admin";

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
