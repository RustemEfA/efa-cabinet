"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function UploadForm({
  userId,
  projectId
}: {
  userId: string;
  projectId: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const supabase = createClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const file = inputRef.current?.files?.[0];
    if (!file) return;

    setBusy(true);
    setError(null);

    // Путь внутри бакета: <user_id>/<project_id>/<timestamp>_<filename>
    // Префикс user_id обязателен — на нём построены Storage-политики
    // (см. supabase/migrations/0002_storage.sql), без него запись
    // отклонит RLS.
    const path = `${userId}/${projectId}/${Date.now()}_${file.name}`;

    const { error: uploadError } = await supabase.storage
      .from("documents")
      .upload(path, file);

    if (uploadError) {
      setError(uploadError.message);
      setBusy(false);
      return;
    }

    const { error: insertError } = await supabase.from("documents").insert({
      project_id: projectId,
      owner_id: userId,
      storage_path: path,
      file_name: file.name,
      file_size: file.size,
      kind: "regulation"
    });

    if (insertError) {
      setError(insertError.message);
      setBusy(false);
      return;
    }

    if (inputRef.current) inputRef.current.value = "";
    setBusy(false);
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} style={{ marginBottom: 8 }}>
      <label htmlFor="file">Загрузить регламент (PDF, DOCX, XLSX)</label>
      <input ref={inputRef} type="file" id="file" name="file" required style={{ color: "var(--white)" }} />
      <button className="btn" type="submit" disabled={busy}>
        {busy ? "Загрузка…" : "Загрузить"}
      </button>
      {error ? <p className="error">{error}</p> : null}
    </form>
  );
}
