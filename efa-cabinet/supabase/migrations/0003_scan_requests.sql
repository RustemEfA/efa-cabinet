-- ============================================================
-- EfA Cabinet — заявки на "Скан репутации" (Шаг 1 дорожной карты).
-- Запускать в Supabase: Dashboard -> SQL Editor -> вставить целиком -> Run.
-- ============================================================

create table if not exists public.scan_requests (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id uuid not null references public.profiles(id) on delete cascade,
  org_name text not null,
  site text,
  social text,
  status text not null default 'submitted', -- submitted | contacted | paid | done
  created_at timestamptz not null default now()
);

alter table public.scan_requests enable row level security;

create policy "scan_requests: select own" on public.scan_requests
  for select using (auth.uid() = owner_id);

create policy "scan_requests: insert own" on public.scan_requests
  for insert with check (auth.uid() = owner_id);
