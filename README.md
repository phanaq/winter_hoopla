# Goaltimate Weekly Signup App

A Streamlit application for managing weekly goaltimate player signups with waitlist functionality and email notifications.

## Features

- **Player Type Selection**: Sign up as MMP (Man Matching Player) or WMP (Woman Matching Player)
- **Weekly Signups**: Sign up for any week (current week + 4 future weeks)
- **Capacity Limits**: Maximum 12 MMP and 12 WMP players per week
- **Automatic Waitlist**: Players beyond the limit are automatically added to an ordered waitlist
- **Self-Removal**: Players can remove themselves from signups
- **Automatic Promotion**: When a player removes themselves, the top waitlist player is automatically promoted
- **Email Notifications**: Promoted players receive email notifications (optional)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run app.py
```

## Email Configuration (Optional)

To enable email notifications for waitlist promotions, you can configure email settings in one of two ways:

### Option 1: Environment Variables
```bash
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SENDER_EMAIL=your-email@gmail.com
export SENDER_PASSWORD=your-app-password
export EMAIL_ENABLED=true
```

### Option 2: Streamlit Secrets

Create a `.streamlit/secrets.toml` file:
```toml
[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "your-email@gmail.com"
sender_password = "your-app-password"
enabled = true
```

**Note**: For Gmail, you'll need to use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

## Data Storage

Player signups and waitlists are stored in `signup_data.json` in the same directory as the app. This file is automatically created and updated as players sign up or remove themselves.

## Usage

1. Enter your name and optional email in the sidebar
2. Use the **Sign Up** tab to register for a week
3. Use the **View Signups** tab to see current signups and waitlists
4. Use the **Remove Signup** tab to cancel your registration

