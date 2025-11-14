# Supabase Setup Guide

This guide will help you set up Supabase (free PostgreSQL database) for persistent storage of your signup data.

## Why Supabase?

- ✅ **Free tier**: 500MB database, 2GB bandwidth per month
- ✅ **Persistent storage**: Data survives app restarts and redeployments
- ✅ **Easy setup**: Simple configuration, no complex setup required
- ✅ **Secure**: Built-in authentication and security features

## Step 1: Create a Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Click **Start your project** or **Sign up**
3. Sign up with GitHub (easiest) or email
4. Verify your email if needed

## Step 2: Create a New Project

1. Click **New Project**
2. Fill in:
   - **Name**: `winter-hoopla` (or any name you like)
   - **Database Password**: Create a strong password (save it somewhere safe)
   - **Region**: Choose closest to you (e.g., `US East (North Virginia)`)
   - **Pricing Plan**: Free (default)
3. Click **Create new project**
4. Wait 1-2 minutes for the project to be created

## Step 3: Get Your API Keys

1. In your Supabase project dashboard, click the **Settings** icon (⚙️) in the left sidebar
2. Click **API** in the settings menu
3. You'll see:
   - **Project URL**: At the top, something like `https://xxxxxxxxxxxxx.supabase.co`
   - **Project API keys** section with:
     - **Publishable key** (also called "anon public" key): A long string starting with `eyJ...` - **Use this one!**
     - **Secret key**: A different long string - Don't use this one for now

**Important**: Use the **Publishable key** (not the Secret key). The Publishable key is safe to use in client-side code.

Copy both the **Project URL** and the **Publishable key** - you'll need them in the next step.

## Step 4: Create the Database Table

1. In your Supabase dashboard, click **SQL Editor** in the left sidebar
2. Click **New query**
3. Copy and paste this SQL:

```sql
-- Create the app_data table
CREATE TABLE IF NOT EXISTS app_data (
  id TEXT PRIMARY KEY,
  data JSONB NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert initial row (if it doesn't exist)
INSERT INTO app_data (id, data)
VALUES ('main', '{"players": {}, "signups": {"mmp": [], "wmp": [], "no_preference": []}, "waitlists": {"mmp": [], "wmp": [], "no_preference": []}}')
ON CONFLICT (id) DO NOTHING;

-- Enable Row Level Security (RLS) - we'll make it public for simplicity
ALTER TABLE app_data ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations (since we're using the anon key)
CREATE POLICY "Allow all operations on app_data" ON app_data
FOR ALL
USING (true)
WITH CHECK (true);
```

4. Click **Run** (or press Ctrl+Enter)
5. You should see "Success. No rows returned"

## Step 5: Configure Streamlit Secrets

### For Local Development

1. Create a `.streamlit` folder in your project root (if it doesn't exist)
2. Create a file called `secrets.toml` in the `.streamlit` folder
3. Add your Supabase credentials:

```toml
[supabase]
url = "https://xxxxxxxxxxxxx.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
enabled = true
```

Replace:
- `url` with your **Project URL** from Step 3
- `key` with your **Publishable key** (not the Secret key) from Step 3

### For Streamlit Cloud Deployment

1. Go to your app on [share.streamlit.io](https://share.streamlit.io)
2. Click the **⚙️ Settings** icon
3. Click **Secrets** in the left sidebar
4. Add your Supabase configuration:

```toml
[supabase]
url = "https://xxxxxxxxxxxxx.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
enabled = true
```

Replace:
- `url` with your **Project URL** from Step 3
- `key` with your **Publishable key** (not the Secret key) from Step 3

5. Click **Save**
6. Your app will automatically redeploy

## Step 6: Test the Connection

1. Run your app locally or check your deployed app
2. Try signing up a test player
3. Check your Supabase dashboard:
   - Go to **Table Editor** in the left sidebar
   - Click on `app_data` table
   - You should see a row with `id = "main"` and your data in the `data` column

## Troubleshooting

### "Failed to load from Supabase"
- Check that your URL and key are correct in secrets
- Verify that `enabled = true` in your secrets
- Check that the table was created successfully (Step 4)

### "Permission denied" or "Row Level Security" errors
- Make sure you ran the SQL policy creation in Step 4
- Verify you're using the **Publishable key** (not the Secret key)

### Data not persisting
- Check Supabase dashboard → Table Editor → app_data to see if data is being saved
- Check Streamlit Cloud logs for any errors
- Verify `enabled = true` in your secrets

### Want to reset all data?
Run this SQL in the SQL Editor:

```sql
UPDATE app_data
SET data = '{"players": {}, "signups": {"mmp": [], "wmp": [], "no_preference": []}, "waitlists": {"mmp": [], "wmp": [], "no_preference": []}}'
WHERE id = 'main';
```

## Security Notes

- The **Publishable key** (anon key) is safe to use in client-side code (it's public)
- Row Level Security (RLS) is enabled but we've set a permissive policy for simplicity
- The **Secret key** should never be used in client-side code - only use it for server-side operations if needed
- Never commit your `secrets.toml` file to git (it's already in `.gitignore`)

## What Happens to Old JSON Data?

The app will automatically:
1. Try to load from Supabase first (if enabled)
2. Fall back to the local `signup_data.json` file if Supabase is not configured
3. Migrate old data structure automatically when loading

You can manually migrate data by:
1. Loading the app with Supabase disabled (reads from JSON)
2. Enabling Supabase (saves to database)
3. The data will be automatically saved to Supabase on the next save operation

---

**Need help?** Check the [Supabase documentation](https://supabase.com/docs) or [Streamlit Cloud documentation](https://docs.streamlit.io/streamlit-community-cloud).

