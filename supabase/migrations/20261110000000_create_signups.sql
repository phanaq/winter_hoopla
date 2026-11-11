-- Winter Hoopla weekly signups.
-- One row per player per session. The roster and waitlist are derived from
-- signup order (created_at), so cancelling a row automatically promotes the
-- next eligible player on the waitlist.

create table if not exists public.signups (
    id              bigint generated always as identity primary key,
    session_date    date        not null,
    name            text        not null,
    email           text        not null,
    gender_match    text        not null check (gender_match in ('mmp', 'wmp', 'xmp')),
    payment_method  text        not null check (payment_method in ('venmo', 'zelle', 'in_person')),
    paid_verified   boolean     not null default false,  -- for the organizer to tick in the dashboard
    created_at      timestamptz not null default now(),
    cancelled_at    timestamptz
);

-- A player can only hold one active signup per session.
create unique index if not exists signups_one_active_per_email
    on public.signups (session_date, lower(email))
    where cancelled_at is null;

create index if not exists signups_session_order
    on public.signups (session_date, created_at, id);

-- Lock the table down: RLS on with no policies means the public anon /
-- publishable key cannot read or write (so player emails stay private).
-- The Streamlit app runs server-side and connects with the secret key,
-- which bypasses RLS.
alter table public.signups enable row level security;
