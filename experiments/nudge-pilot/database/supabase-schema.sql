-- Fukui nudge pilot response table.
-- Run this in Supabase SQL Editor before deploying the Vercel app.

create extension if not exists pgcrypto;

create table if not exists public.nudge_pilot_responses (
  id uuid primary key default gen_random_uuid(),
  study_id text not null,
  study_version text not null,
  session_id text not null unique,
  assigned_condition text not null,
  started_at timestamptz not null,
  completed_at timestamptz not null,
  consent boolean not null default false,
  background jsonb not null default '{}'::jsonb,
  tasks jsonb not null default '{}'::jsonb,
  surveys jsonb not null default '{}'::jsonb,
  final_responses jsonb not null default '{}'::jsonb,
  events jsonb not null default '[]'::jsonb,
  flattened jsonb not null default '{}'::jsonb,
  user_agent text,
  app_source text not null default 'vercel',
  received_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists nudge_pilot_responses_study_id_idx
  on public.nudge_pilot_responses (study_id);

create index if not exists nudge_pilot_responses_condition_idx
  on public.nudge_pilot_responses (assigned_condition);

create index if not exists nudge_pilot_responses_completed_at_idx
  on public.nudge_pilot_responses (completed_at);

create or replace function public.set_nudge_pilot_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_nudge_pilot_responses_updated_at
  on public.nudge_pilot_responses;

create trigger set_nudge_pilot_responses_updated_at
before update on public.nudge_pilot_responses
for each row
execute function public.set_nudge_pilot_updated_at();

alter table public.nudge_pilot_responses enable row level security;

-- The browser never talks directly to Supabase in this implementation.
-- Vercel API routes insert rows with SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS.
-- These deny-by-default policies prevent anonymous browser clients from reading
-- or writing the table if the public Supabase URL is ever exposed elsewhere.
drop policy if exists "deny anonymous reads" on public.nudge_pilot_responses;
drop policy if exists "deny anonymous writes" on public.nudge_pilot_responses;

create policy "deny anonymous reads"
on public.nudge_pilot_responses
for select
to anon
using (false);

create policy "deny anonymous writes"
on public.nudge_pilot_responses
for insert
to anon
with check (false);

-- Useful export view: one row per participant with common SEM columns.
-- The raw table remains the source of truth.
create or replace view public.nudge_pilot_sem_export as
select
  id,
  study_id,
  study_version,
  session_id,
  assigned_condition,
  started_at,
  completed_at,
  received_at,
  flattened
from public.nudge_pilot_responses
order by completed_at;
