-- Waitlisted players aren't asked about payment, and players moved up from the
-- waitlist are emailed payment options, so payment_method can be blank.
alter table public.signups alter column payment_method drop not null;
