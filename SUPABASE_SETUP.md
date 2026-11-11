# Supabase Setup

Signups are stored in the `signups` table in Supabase project `kywdoikmrtpzhbxicnxv`.
The schema lives in [`supabase/migrations/`](supabase/migrations/).

## One-time CLI setup

```bash
brew install supabase/tap/supabase
supabase login
supabase link --project-ref kywdoikmrtpzhbxicnxv   # asks for the database password
supabase db push                                    # applies migrations
```

## Secrets

Copy `.streamlit/secrets.toml.template` to `.streamlit/secrets.toml` and fill in the
**secret** key (Dashboard → Project Settings → API Keys). Paste the same contents
into Streamlit Cloud → App settings → Secrets.

The table has Row Level Security enabled with no policies, so the public/anon key
can't read player emails. The Streamlit app runs server-side, so the secret key is
never sent to browsers.

## How signups work

- One row per player per Monday (`session_date`). Cancelling sets `cancelled_at`.
- The roster is computed in signup order: 10 MMP + 10 WMP spots. Everyone else
  is on the waitlist, and when someone
  cancels, newly rostered players are emailed.
- Signups for each Monday open the Friday before at 5pm Central (`SIGNUP_OPEN_*` in `app.py`).
- `payment_method` is what the player selected (venmo / zelle / in_person). Tick
  `paid_verified` in the Table Editor once you've seen the payment.

## Handy queries (SQL editor)

```sql
-- This week's active signups in order
select name, email, gender_match, payment_method, paid_verified, created_at
from signups
where session_date = '2026-11-16' and cancelled_at is null
order by created_at, id;
```

## Previewing other times locally

```bash
HOOPLA_NOW="2026-11-13 17:05" streamlit run app.py
```
