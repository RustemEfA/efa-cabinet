-- ============================================================
-- EfA Cabinet — партнёрская программа.
-- Запускать в Supabase: Dashboard -> SQL Editor -> вставить целиком -> Run.
-- Запускать ПОСЛЕ 0001-0003.
-- ============================================================

-- 1. Партнёры (агенты, которые приводят клиентов по промокоду)
create table if not exists public.partners (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  email text not null unique,
  phone text,
  promo_code text not null unique,
  commission_rate numeric not null default 0.50,       -- доля партнёра от суммы, оплаченной клиентом
  client_discount_rate numeric not null default 0.10,   -- скидка клиенту по промокоду
  auth_user_id uuid references auth.users(id) on delete set null,
  status text not null default 'active', -- active | paused
  created_at timestamptz not null default now()
);

alter table public.partners enable row level security;

create policy "partners: select own" on public.partners
  for select using (auth.uid() = auth_user_id);

-- 2. Привязка клиента к партнёру — разово при регистрации, дальше не меняется.
--    partner_discount_rate — снимок скидки НА МОМЕНТ регистрации (чтобы более
--    поздние изменения ставки у партнёра не задевали уже привязанных клиентов).
alter table public.profiles
  add column if not exists partner_id uuid references public.partners(id) on delete set null,
  add column if not exists promo_code_used text,
  add column if not exists partner_discount_rate numeric;

-- 3. Учётная таблица начислений — одна строка на каждую оплату клиента
--    (Шаг 1, Шаг 2, и все будущие платные шаги).
create table if not exists public.partner_orders (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  partner_id uuid not null references public.partners(id) on delete cascade,
  order_kind text not null,               -- 'scan' | 'interview'
  client_label text,                      -- снимок названия клиента на момент создания строки
  gross_amount numeric not null,          -- полная цена услуги
  discount_amount numeric not null default 0,
  client_paid_amount numeric,             -- сколько реально заплатил клиент (после скидки)
  client_paid_at timestamptz,
  commission_amount numeric,              -- = client_paid_amount * partner.commission_rate
  commission_status text not null default 'pending', -- pending | accrued | paid
  commission_paid_amount numeric,
  commission_paid_at timestamptz,
  created_at timestamptz not null default now(),
  unique (project_id, order_kind)
);

alter table public.partner_orders enable row level security;

create policy "partner_orders: select own" on public.partner_orders
  for select using (
    partner_id in (select id from public.partners where auth_user_id = auth.uid())
  );

-- 4. Обновлённое автосоздание профиля: попутно чиним старый баг (форма
--    регистрации собирала company_name, но триггер его не сохранял) и
--    привязываем партнёра, если при регистрации введён действующий промокод.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
declare
  matched_partner_id uuid;
  matched_discount_rate numeric;
  entered_code text;
begin
  entered_code := nullif(trim(new.raw_user_meta_data->>'promo_code'), '');

  if entered_code is not null then
    select id, client_discount_rate into matched_partner_id, matched_discount_rate
    from public.partners
    where lower(promo_code) = lower(entered_code)
      and status = 'active'
    limit 1;
  end if;

  insert into public.profiles (id, company_name, contact_name, partner_id, promo_code_used, partner_discount_rate)
  values (
    new.id,
    new.raw_user_meta_data->>'company_name',
    new.raw_user_meta_data->>'contact_name',
    matched_partner_id,
    entered_code,
    matched_discount_rate
  );
  return new;
end;
$$;
