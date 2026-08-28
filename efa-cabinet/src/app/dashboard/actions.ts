"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function createProject(formData: FormData) {
  const title = String(formData.get("title") || "Новый проект");

  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  await supabase.from("projects").insert({ owner_id: user.id, title });
  revalidatePath("/dashboard");
  redirect("/dashboard#projects");
}
