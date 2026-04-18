-- Module 4 shared schema for Supabase
-- Run this in Supabase SQL Editor once.

create table if not exists module4_client_visits (
  id bigint generated always as identity primary key,
  visit_id text unique not null,
  client_name text not null,
  customer_segment text,
  saved_at timestamptz,
  raw_transcript_ca text,

  summary text,
  target_recipients jsonb,
  life_event jsonb,
  timeline jsonb,
  aesthetic_preference jsonb,
  size_height jsonb,
  budget jsonb,
  mood jsonb,
  trend_signals jsonb,
  next_step_intent jsonb,
  interested_items jsonb,
  client_constraints jsonb,
  purchase_frequency jsonb,
  visit_purpose jsonb,
  purchase_decision_status jsonb,
  positive_signals jsonb,
  negative_reasons jsonb,
  client_timeline jsonb,
  ca_action_item jsonb,

  l1_client_profile jsonb,
  l2_constraints jsonb,
  l3_visit_funnel jsonb,
  l4_next_steps jsonb,

  full_profile jsonb not null,
  source text default 'module4_streamlit',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_module4_client_visits_client_name
  on module4_client_visits (client_name);

create index if not exists idx_module4_client_visits_saved_at
  on module4_client_visits (saved_at desc);

create index if not exists idx_module4_client_visits_full_profile
  on module4_client_visits using gin (full_profile);

create or replace function module4_set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_module4_client_visits_updated_at on module4_client_visits;
create trigger trg_module4_client_visits_updated_at
before update on module4_client_visits
for each row execute function module4_set_updated_at();

create or replace view module4_clients_latest as
select distinct on (client_name)
  client_name,
  visit_id,
  saved_at,
  summary,
  full_profile
from module4_client_visits
order by client_name, saved_at desc;
