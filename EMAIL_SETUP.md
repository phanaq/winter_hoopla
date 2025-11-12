# Email Notification Setup Guide

This guide will help you set up email notifications for waitlist promotions.

## Quick Setup (Recommended: Streamlit Secrets)

### Step 1: Create the secrets file

Create a `.streamlit` directory in your project root (if it doesn't exist) and create a `secrets.toml` file:

```bash
mkdir -p .streamlit
touch .streamlit/secrets.toml
```

### Step 2: Get a Gmail App Password

1. Go to your Google Account: https://myaccount.google.com/
2. Click on **Security** in the left sidebar
3. Under "How you sign in to Google", click **2-Step Verification** (enable it if not already enabled)
4. After enabling 2-Step Verification, go back to Security
5. Under "How you sign in to Google", click **App passwords**
6. Select "Mail" as the app and "Other (Custom name)" as the device
7. Enter "Goaltimate Signup" as the name
8. Click **Generate**
9. Copy the 16-character password (it will look like: `abcd efgh ijkl mnop`)

### Step 3: Configure Streamlit Secrets

Edit `.streamlit/secrets.toml` and add:

```toml
[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "your-email@gmail.com"
sender_password = "your-16-character-app-password"
enabled = true
```

**Important**: 
- Replace `your-email@gmail.com` with your actual Gmail address
- Replace `your-16-character-app-password` with the app password from Step 2 (remove spaces)
- Make sure `enabled = true` (not in quotes)

### Step 4: Restart the Streamlit app

After saving the secrets file, restart your Streamlit app:

```bash
streamlit run app.py
```

The app will automatically load the email configuration. You should see "✅ Email notifications enabled" at the bottom of the app.

---

## Alternative: Environment Variables

If you prefer using environment variables instead:

### For macOS/Linux:

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SENDER_EMAIL=your-email@gmail.com
export SENDER_PASSWORD=your-16-character-app-password
export EMAIL_ENABLED=true
```

Then reload your shell:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### For Windows (PowerShell):

```powershell
$env:SMTP_SERVER="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SENDER_EMAIL="your-email@gmail.com"
$env:SENDER_PASSWORD="your-16-character-app-password"
$env:EMAIL_ENABLED="true"
```

---

## Using Other Email Providers

### Outlook/Office 365:
```toml
[email]
smtp_server = "smtp.office365.com"
smtp_port = 587
sender_email = "your-email@outlook.com"
sender_password = "your-password"
enabled = true
```

### Yahoo:
```toml
[email]
smtp_server = "smtp.mail.yahoo.com"
smtp_port = 587
sender_email = "your-email@yahoo.com"
sender_password = "your-app-password"
enabled = true
```

### Custom SMTP Server:
```toml
[email]
smtp_server = "smtp.yourdomain.com"
smtp_port = 587  # or 465 for SSL
sender_email = "noreply@yourdomain.com"
sender_password = "your-password"
enabled = true
```

---

## Testing Email Notifications

1. Sign up two players for the same week and player type
2. Have one player remove their signup
3. The waitlisted player should receive an email notification

---

## Troubleshooting

### "Failed to send email" error
- Verify your app password is correct (no spaces)
- Make sure 2-Step Verification is enabled on your Google account
- Check that `enabled = true` in your secrets file
- Verify SMTP server and port are correct for your email provider

### Email not sending
- Check that the recipient's email address is valid
- Verify your email provider allows SMTP access
- Some email providers require you to enable "Less secure app access" (not recommended - use app passwords instead)

### Secrets not loading
- Make sure the file is at `.streamlit/secrets.toml` (relative to your project root)
- Restart the Streamlit app after creating/modifying secrets
- Check for syntax errors in the TOML file

---

## Security Notes

⚠️ **Important**: Never commit your `secrets.toml` file to version control!

Make sure `.streamlit/secrets.toml` is in your `.gitignore` file:

```bash
echo ".streamlit/secrets.toml" >> .gitignore
```

