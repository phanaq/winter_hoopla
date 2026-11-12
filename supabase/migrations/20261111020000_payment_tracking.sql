-- Payment, refund and attendance tracking for the organizer admin app (admin.py).
-- Safe to run more than once. paid_verified stays the source of truth for
-- "paid"; the admin tool sets it to true whenever it records a payment.
alter table public.signups add column if not exists amount_paid   numeric(8,2);
alter table public.signups add column if not exists paid_via      text;
alter table public.signups add column if not exists paid_at       timestamptz;
alter table public.signups add column if not exists payment_ref   text;  -- statement transaction id, prevents double imports
alter table public.signups add column if not exists refund_status text;
alter table public.signups add column if not exists refund_amount numeric(8,2);
alter table public.signups add column if not exists refunded_at   timestamptz;
alter table public.signups add column if not exists admin_notes   text;
-- Attendance taken at the field: null = not taken yet, true = showed up, false = no-show.
alter table public.signups add column if not exists attended           boolean;
alter table public.signups add column if not exists attended_marked_at timestamptz;

alter table public.signups drop constraint if exists signups_paid_via_check;
alter table public.signups
    add constraint signups_paid_via_check check (paid_via in ('venmo', 'zelle', 'cash'));

alter table public.signups drop constraint if exists signups_refund_status_check;
alter table public.signups
    add constraint signups_refund_status_check check (refund_status in ('owed', 'refunded', 'not_needed'));
