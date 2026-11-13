-- One row per player who has signed the Winter Hoopla waiver. The waiver has no
-- expiration, so players sign it once and it covers every week and season.
-- Keyed by lowercased email, the same email players use to sign up.
create table if not exists public.waivers (
    email      text primary key check (email = lower(email)),
    name       text not null,
    signed_at  timestamptz not null default now(),
    notes      text
);

alter table public.waivers enable row level security;  -- no policies: only the secret key can read it
