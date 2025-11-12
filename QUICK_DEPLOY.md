# Quick Deploy Checklist

## ✅ Pre-Deployment Checklist

- [x] Git repository initialized
- [x] `.gitignore` configured (secrets and data files excluded)
- [x] `requirements.txt` ready
- [x] App code complete

## 🚀 Deploy in 5 Steps

### 1. Commit your code
```bash
git commit -m "Ready for deployment"
```

### 2. Create GitHub repository
- Go to https://github.com/new
- Name it (e.g., `winter-hoopla-signup`)
- Choose **Public** (required for free Streamlit Cloud)
- Click **Create repository**

### 3. Push to GitHub
```bash
# Replace YOUR_USERNAME and REPO_NAME with your actual values
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
git branch -M main
git push -u origin main
```

### 4. Deploy to Streamlit Cloud
- Go to https://share.streamlit.io
- Sign in with GitHub
- Click **New app**
- Select your repository
- Main file: `app.py`
- Click **Deploy!**

### 5. Add Email Secrets
- In Streamlit Cloud, go to app settings (⚙️)
- Click **Secrets**
- Paste your email config (from `.streamlit/secrets.toml`)
- Click **Save**

## 📧 Email Configuration for Streamlit Cloud

In Streamlit Cloud Secrets, add:

```toml
[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "your-email@gmail.com"
sender_password = "your-16-char-app-password"
enabled = true
```

## 🔗 Your App URL

After deployment, your app will be at:
`https://YOUR_APP_NAME.streamlit.app`

## ⚠️ Important Notes

- **Data will reset** on each deployment (file-based storage)
- For production, consider using a database
- Secrets are secure in Streamlit Cloud (encrypted)

## 📚 Full Guide

See `DEPLOYMENT.md` for detailed instructions and troubleshooting.

