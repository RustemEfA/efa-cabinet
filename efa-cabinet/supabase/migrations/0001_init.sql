-- ============================================================
-- EfA Cabinet — базовая схема (каркас фазы 1).
-- Запускать в Supabase: Dashboard → SQL Editor → вставить целиком → Run.
-- Ничего не автоматизирует само по себе — только хранит данные и
-- закрывает доступ так, чтобы клиент видел только свои проекты.
-- ============================================================

-- 1. Профиль клиента (создаётся автоматически при регистрации через триггер ниже)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  company_name text,
  contact_name text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles: select own" on public.profiles
  for select using (auth.uid() = id);

create policy "profiles: update own" on public.profiles
  for update using (auth.uid() = id);

-- Автосоздание профиля при регистрации нового пользователя
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, contact_name)
  values (new.id, new.raw_user_meta_data->>'contact_name');
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();


-- 2. Проекты. Один клиент может завести несколько (например, несколько своих
--    заказчиков, на каждого — отдельная бизнес-архитектура).
--    status — простой текстовый статус, никакой автоматики его не меняет
--    сама (это делает Рустем вручную через дашборд/SQL, пока нет фазы 3).
create type public.project_status as enum (
  'draft',            -- клиент только завёл проект
  'awaiting_docs',    -- ждём регламенты от клиента
  'survey_open',      -- ссылка на опрос выдана, ждём ответы сотрудников
  'processing',       -- данные собраны, идёт сборка бизнес-архитектуры (вручную)
  'done'              -- результат загружен, клиент может скачать
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles(id) on delete cascade,
  title text not null default 'Новый проект',
  status public.project_status not null default 'draft',
  survey_token text unique, -- используется в deep-link на Telegram-бота (?start=<survey_token>), заполняется вручную на фазе 1
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.projects enable row level security;

create policy "projects: select own" on public.projects
  for select using (auth.uid() = owner_id);

create policy "projects: insert own" on public.projects
  for insert with check (auth.uid() = owner_id);

create policy "projects: update own" on public.projects
  for update using (auth.uid() = owner_id);


-- 3. Загруженные документы (регламенты и т.п.) — метаданные файла.
--    Сам файл лежит в Storage-бакете "documents" (см. README/скрипт бакета
--    ниже), здесь только ссылка на путь + кто/когда загрузил.
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id uuid not null references public.profiles(id) on delete cascade,
  storage_path text not null,     -- путь внутри бакета "documents"
  file_name text not null,
  file_size bigint,
  kind text not null default 'regulation', -- regulation | survey_result | deliverable
  created_at timestamptz not null default now()
);

alter table public.documents enable row level security;

create policy "documents: select own" on public.documents
  for select using (auth.uid() = owner_id);

create policy "documents: insert own" on public.documents
  for insert with check (auth.uid() = owner_id);

create policy "documents: delete own" on public.documents
  for delete using (auth.uid() = owner_id);


-- 4. Готовые результаты (HTML-пакет регламентов и т.п.) — та же таблица
--    documents, kind='deliverable'. Отдельной таблицы не заводим, чтобы
--    не дублировать логику доступа/RLS.

-- 5. Триггер updated_at на projects
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists projects_touch_updated_at on public.projects;
create trigger projects_touch_updated_at
  before update on public.projects
  for each row execute procedure public.touch_updated_at();
