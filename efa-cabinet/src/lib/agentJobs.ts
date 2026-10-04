// Задания ИИ-агентов: кабинет ставит задание в очередь (таблица agent_jobs),
// обработчик worker/ (Python, отдельный контейнер) выполняет его и пишет
// ход работы, результат и файлы. Здесь — только серверный код: вставка идёт
// через service role, поэтому вызывать ТОЛЬКО из server actions / route
// handlers ПОСЛЕ проверки, что проект принадлежит пользователю и оплачен.
import { createAdminClient } from "@/lib/supabase/admin";

export type AgentName = "business_architect";
export type AgentJobStatus = "queued" | "running" | "done" | "failed" | "cancelled";

// Вход «Бизнес-архитектора» — анкета клиента (см. worker/efa_agents/business_architect/pipeline.py)
export type BusinessArchitectInput = {
  company: string;
  brief: string;               // анкета / досье Квалификатора текстом
  headcount?: number;
  systems?: string[];          // учётные системы, которые уже есть: ["1С", "CRM"]
  units?: string[];            // дополнительные обязательные подразделения
  flagship?: string;           // ключевой процесс для детализации и BPMN
  options?: { passports?: "heads" | "all" | "none"; bpmn?: boolean; documents?: boolean; audit?: boolean };
  previous_job_id?: string;    // итерация: результат какого задания править
  remarks?: string;            // итерация: замечания клиента
};

export type AgentJob = {
  id: string;
  project_id: string;
  agent: AgentName;
  status: AgentJobStatus;
  progress: { stage?: string; step?: string; at?: string } | null;
  result: any;
  error: string | null;
  created_at: string;
  finished_at: string | null;
};

export async function enqueueAgentJob(params: {
  projectId: string;
  ownerId: string;
  agent: AgentName;
  input: BusinessArchitectInput;
  priceRub?: number;
}): Promise<string | null> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("agent_jobs")
    .insert({
      project_id: params.projectId,
      owner_id: params.ownerId,
      agent: params.agent,
      input: params.input,
      price_rub: params.priceRub ?? null
    })
    .select("id")
    .single();
  if (error || !data) return null;
  return data.id as string;
}

// Чтение — обычным клиентом пользователя: RLS отдаёт только его задания.
export async function getAgentJob(supabase: any, jobId: string): Promise<AgentJob | null> {
  const { data } = await supabase
    .from("agent_jobs")
    .select("id, project_id, agent, status, progress, result, error, created_at, finished_at")
    .eq("id", jobId)
    .maybeSingle();
  return (data as AgentJob) ?? null;
}

export async function listProjectJobs(supabase: any, projectId: string): Promise<AgentJob[]> {
  const { data } = await supabase
    .from("agent_jobs")
    .select("id, project_id, agent, status, progress, error, created_at, finished_at")
    .eq("project_id", projectId)
    .order("created_at", { ascending: false });
  return (data as AgentJob[]) ?? [];
}

export async function listJobArtifacts(supabase: any, jobId: string): Promise<{ name: string; content_type: string }[]> {
  const { data } = await supabase
    .from("agent_artifacts")
    .select("name, content_type")
    .eq("job_id", jobId)
    .order("name");
  return data ?? [];
}
