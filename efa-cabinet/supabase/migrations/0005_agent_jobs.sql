-- ============================================================
-- EfA Cabinet — задания ИИ-агентов (очередь для обработчика worker/).
-- Запускать в Supabase: Dashboard -> SQL Editor -> вставить целиком -> Run.
-- Запускать ПОСЛЕ 0001-0004. Обычный Postgres — переносится в Yandex Managed PostgreSQL без правок
-- (кроме политик RLS, которые опираются на auth.uid() Supabase).
--
-- Как работает: кабинет (Next.js) вставляет строку в agent_jobs со статусом queued.
-- Обработчик забирает её (FOR UPDATE SKIP LOCKED), пишет ход работы в progress,
-- результат — в result, файлы (BPMN, скрипты Sila) — в agent_artifacts, расход моделей — в agent_usage.
-- ============================================================

create table if not exists public.agent_jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id uuid not null references public.profiles(id) on delete cascade,
  agent text not null,                      -- 'business_architect' | позже: 'qualifier', 'script', ...
  status text not null default 'queued',    -- queued | running | done | failed | cancelled
  input jsonb not null,                     -- анкета, численность, системы; для итерации — previous_job_id и remarks
  progress jsonb,                           -- {stage, step, rub_total, ...} — для полосы хода в кабинете
  result jsonb,                             -- разделы архитектуры, аудит, замечания для консультанта
  error text,
  price_rub numeric,                        -- цена для клиента (списание с кошелька — после переделки кошелька)
  cost_rub numeric,                         -- себестоимость моделей по журналу
  tokens_in integer,
  tokens_out integer,
  attempts integer not null default 0,
  locked_by text,
  heartbeat_at timestamptz,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create index if not exists agent_jobs_queue on public.agent_jobs (created_at) where status = 'queued';
create index if not exists agent_jobs_project on public.agent_jobs (project_id, created_at desc);

alter table public.agent_jobs enable row level security;

create policy "agent_jobs: select own" on public.agent_jobs
  for select using (auth.uid() = owner_id);
-- вставляет задания только сервер кабинета (service role) — после проверки оплаты; клиенту insert не даём


-- Файлы результата: BPMN, скрипты Sila Union, исходные JSON схем
create table if not exists public.agent_artifacts (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.agent_jobs(id) on delete cascade,
  name text not null,                       -- 'bpmn/flow_top.bpmn'
  content_type text not null default 'text/plain',
  body text not null,
  created_at timestamptz not null default now(),
  unique (job_id, name)
);

alter table public.agent_artifacts enable row level security;

create policy "agent_artifacts: select own" on public.agent_artifacts
  for select using (job_id in (select id from public.agent_jobs where owner_id = auth.uid()));


-- Журнал расхода моделей: шаг, модель, токены, ₽ — для себестоимости и проверки финмодели
create table if not exists public.agent_usage (
  id bigserial primary key,
  job_id uuid not null references public.agent_jobs(id) on delete cascade,
  step text not null,
  role text,                                -- author | mass | auditor | fallback
  model text,
  tokens_in integer not null default 0,
  tokens_out integer not null default 0,
  cost_rub numeric not null default 0,
  sec numeric,
  attempts integer,
  errors_left integer,
  fallback boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists agent_usage_job on public.agent_usage (job_id);

alter table public.agent_usage enable row level security;
-- клиенту журнал не показываем (только администратор через service role)
