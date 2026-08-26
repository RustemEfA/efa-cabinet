import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { statusLabel } from "@/lib/statusLabels";
import UploadForm from "./UploadForm";

function formatBytes(bytes: number | null) {
  if (!bytes) return "";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} КБ`;
  return `${(kb / 1024).toFixed(1)} МБ`;
}

export default async function ProjectPage({
  params
}: {
  params: { projectId: string };
}) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: project } = await supabase
    .from("projects")
    .select("id, title, status, survey_token, created_at")
    .eq("id", params.projectId)
    .single();

  if (!project) notFound();

  const { data: documents } = await supabase
    .from("documents")
    .select("id, file_name, file_size, kind, storage_path, created_at")
    .eq("project_id", project.id)
    .order("created_at", { ascending: false });

  const regulations = (documents || []).filter((d) => d.kind === "regulation");
  const deliverables = (documents || []).filter((d) => d.kind === "deliverable");

  // Подписанные ссылки на скачивание — бакет приватный, прямых URL нет.
  const withSignedUrls = async (docs: typeof deliverables) => {
    const result = [];
    for (const doc of docs) {
      const { data } = await supabase.storage
        .from("documents")
        .createSignedUrl(doc.storage_path, 60 * 60); // 1 час
      result.push({ ...doc, url: data?.signedUrl || null });
    }
    return result;
  };

  const deliverablesWithUrls = await withSignedUrls(deliverables);

  const surveyUrl = project.survey_token
    ? `https://t.me/YOUR_BOT_USERNAME?start=${project.survey_token}`
    : null;

  return (
    <>
      <p className="eyebrow"><Link href="/dashboard">← Все проекты</Link></p>
      <div className="card-row" style={{ marginBottom: 4 }}>
        <h1 style={{ marginBottom: 0 }}>{project.title}</h1>
        <span className={`badge ${project.status}`}>{statusLabel(project.status)}</span>
      </div>
      <p className="lead">Создан {new Date(project.created_at).toLocaleDateString("ru-RU")}</p>

      <h2 style={{ fontSize: 16, marginTop: 32 }}>Регламенты и исходные данные</h2>
      <p className="lead" style={{ marginBottom: 12 }}>
        Загрузите то, что у вас уже есть: штатное расписание, должностные инструкции, регламенты процессов.
        Чем больше загружено, тем меньше вопросов останется в опросе сотрудников.
      </p>
      <UploadForm userId={user.id} projectId={project.id} />

      {regulations.length === 0 ? (
        <p className="empty">Файлов пока нет.</p>
      ) : (
        regulations.map((doc) => (
          <div className="doc-row" key={doc.id}>
            <span>{doc.file_name}</span>
            <span className="doc-meta">{formatBytes(doc.file_size)}</span>
          </div>
        ))
      )}

      <h2 style={{ fontSize: 16, marginTop: 32 }}>Опрос сотрудников</h2>
      {surveyUrl ? (
        <p className="lead">
          Ссылка для сотрудников: <a href={surveyUrl}>{surveyUrl}</a>
        </p>
      ) : (
        <p className="empty">
          Ссылка появится здесь после того, как мы обработаем загруженные регламенты
          и подготовим вопросы под вашу компанию.
        </p>
      )}

      <h2 style={{ fontSize: 16, marginTop: 32 }}>Результат</h2>
      {deliverablesWithUrls.length === 0 ? (
        <p className="empty">Готовые файлы появятся здесь после сборки бизнес-архитектуры.</p>
      ) : (
        deliverablesWithUrls.map((doc) => (
          <div className="doc-row" key={doc.id}>
            <span>{doc.file_name}</span>
            {doc.url ? <a className="btn secondary" style={{ marginTop: 0 }} href={doc.url}>Скачать</a> : null}
          </div>
        ))
      )}
    </>
  );
}
