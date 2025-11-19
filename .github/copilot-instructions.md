# Copilot Instructions for Goaltimate Signup App

## Project Overview
- **Purpose:** Streamlit app for weekly goaltimate signups, with waitlist and optional email notifications.
- **Main file:** `app.py` (all logic, UI, and data handling)
- **Data storage:**
  - Default: `signup_data.json` (local JSON, auto-created/updated)
  - Optional: Supabase (if configured via env vars or Streamlit secrets)
- **Email notifications:**
  - Optional, for waitlist promotions
  - Configured via environment variables or `.streamlit/secrets.toml`

## Key Workflows
- **Run locally:**
  ```bash
  pip install -r requirements.txt
  streamlit run app.py
  ```
- **Data reset:** Data is reset each week; structure migration logic is in `_normalize_data_structure()`
- **Email setup:** See `EMAIL_SETUP.md` or README for details
- **Supabase setup:** See `SUPABASE_SETUP.md` for cloud storage

## Project-Specific Patterns
- **Player types:** `mmp` (Man Matching), `wmp` (Woman Matching), `no_preference`
- **Capacity:** 12 per type per week (see `MAX_PLAYERS_PER_TYPE`)
- **Waitlist:** Ordered, auto-promotes on removal
- **Data model:**
  - `signups` and `waitlists` are dicts keyed by player type
  - `players` dict holds player info
- **Config precedence:**
  1. Streamlit secrets
  2. Environment variables
  3. Defaults in code
- **Supabase:**
  - Table: `app_data`, row id: `main`, field: `data`
  - Fallback to local file if Supabase fails

## Integration Points
- **Streamlit:** All UI and state
- **Supabase:** Optional, for cloud data persistence
- **SMTP:** Optional, for email notifications

## Conventions
- All logic is in `app.py` (single-file app)
- Data structure migration handled on load
- No tests or CI/CD scripts present
- No custom build steps; just run with Streamlit

## References
- See `README.md`, `EMAIL_SETUP.md`, `SUPABASE_SETUP.md` for setup and usage
- Example config for email/Supabase in README

---
**If adding new features:**
- Follow the single-file pattern unless refactoring for scale
- Update data migration logic if changing data structure
- Document new env vars or secrets in README
