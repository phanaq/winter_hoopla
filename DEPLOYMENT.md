# Deployment Guide - Streamlit Cloud

This guide will help you deploy your Goaltimate Signup app to Streamlit Cloud (free hosting).

## Prerequisites

1. A GitHub account (free)
2. Git installed on your computer
3. Your app code ready to deploy

## Step 1: Initialize Git Repository

If you haven't already, initialize a git repository:

```bash
git init
git add .
git commit -m "Initial commit - Goaltimate signup app"
```

## Step 2: Create GitHub Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click the **+** icon in the top right → **New repository**
3. Name it something like `goaltimate-signup` or `winter-hoopla-signup`
4. Choose **Public** (Streamlit Cloud free tier requires public repos) or **Private** (if you have a paid GitHub account)
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click **Create repository**

## Step 3: Push to GitHub

GitHub will show you commands. Run these in your terminal:

```bash
# Add your GitHub repository as remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
git branch -M main
git push -u origin main
```

## Step 4: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **New app**
4. Fill in:
   - **Repository**: Select your repository
   - **Branch**: `main` (or `master`)
   - **Main file path**: `app.py`
   - **App URL**: Choose a unique URL (e.g., `winter-hoopla-signup`)
5. Click **Deploy!**

## Step 5: Configure Secrets in Streamlit Cloud

After deployment, you need to add your email secrets:

1. In Streamlit Cloud, go to your app's settings (⚙️ icon)
2. Click **Secrets** in the left sidebar
3. Add your email configuration:

```toml
[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "your-email@gmail.com"
sender_password = "your-app-password"
enabled = true
```

4. Click **Save**
5. Your app will automatically redeploy with the new secrets

## Step 6: Update App URL

Your app will be live at: `https://YOUR_APP_NAME.streamlit.app`

Share this URL with your players!

---

## Alternative: Deploy to Other Platforms

### Heroku

1. Install Heroku CLI
2. Create `Procfile`:
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```
3. Deploy:
   ```bash
   heroku create your-app-name
   heroku config:set SMTP_SERVER=smtp.gmail.com
   heroku config:set SMTP_PORT=587
   heroku config:set SENDER_EMAIL=your-email@gmail.com
   heroku config:set SENDER_PASSWORD=your-app-password
   heroku config:set EMAIL_ENABLED=true
   git push heroku main
   ```

### Railway

1. Connect your GitHub repo to Railway
2. Add environment variables in Railway dashboard
3. Deploy automatically

### DigitalOcean App Platform

1. Connect GitHub repo
2. Configure environment variables
3. Deploy

---

## Important Notes

⚠️ **Data Persistence**: The `signup_data.json` file will be reset on each deployment unless you:
- Use a database (PostgreSQL, MongoDB, etc.)
- Use cloud storage (AWS S3, Google Cloud Storage)
- Use Streamlit's built-in database features

For production, consider migrating to a proper database.

⚠️ **Secrets Security**: Never commit your `secrets.toml` file. It's already in `.gitignore`.

---

## Troubleshooting

### App won't deploy
- Check that `app.py` is in the root directory
- Verify `requirements.txt` is correct
- Check Streamlit Cloud logs for errors

### Email not working
- Verify secrets are set correctly in Streamlit Cloud
- Check that app password is correct (no spaces)
- Review Streamlit Cloud logs for email errors

### Data resets
- This is expected with file-based storage
- Consider upgrading to a database for production use

