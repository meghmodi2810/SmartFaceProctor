# 📧 Brevo (Sendinblue) Email Setup Guide - HTTP API

## ✅ Configuration Complete!

Your application is now configured to use **Brevo HTTP API** for sending emails in production (bypassing SMTP port blocking).

---

## 🔑 Step 1: Get Your Brevo API Key

1. **Login to Brevo**: https://app.brevo.com/
2. Go to **Settings** → **SMTP & API**
3. Click on **API Keys** tab
4. Click **Generate a new API key** or **Create a new API key**
5. Give it a name like "Smart Face Proctor Production"
6. Copy the API key (starts with `xkeysib-...`)

**Important**: This is the **API Key** (NOT SMTP key). It's different!

---

## 🚀 Step 2: Add Environment Variables to Render

Go to your Render Dashboard → Your Web Service → **Environment** tab and add this variable:

```
BREVO_API_KEY=xkeysib-your-api-key-here
FROM_EMAIL=meghmodi4ever@gmail.com
ENV=render
```

**Remove these old variables if they exist:**
- ~~BREVO_SMTP_USER~~ (not needed with HTTP API)
- ~~BREVO_SMTP_KEY~~ (not needed with HTTP API)
- ~~SENDGRID_API_KEY~~ (old provider)

---

## ✉️ Step 3: Verify Your Sender Email in Brevo

1. Go to **Senders** in Brevo dashboard
2. Click **Add a Sender**
3. Add your email: `meghmodi4ever@gmail.com`
4. Verify it by clicking the link in the verification email
5. Wait for approval (usually instant for Gmail addresses)

---

## 🧪 Step 4: Deploy and Test

1. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Switch to Brevo HTTP API for email sending"
   git push
   ```

2. **Wait for Render to deploy** (auto-deploys from GitHub)

3. **Check the logs** in Render - you should see:
   ```
   ✅ Brevo API configured - using HTTP API (no SMTP)
   ```

4. **Test email sending**:
   - Try the **Forgot Password** feature
   - Or try **Registration** with OTP

---

## 📊 Why HTTP API Instead of SMTP?

| Method | Port | Issue on Render |
|--------|------|-----------------|
| SMTP | 587 | ❌ **Blocked** (timeout errors) |
| HTTP API | 443 (HTTPS) | ✅ **Works perfectly** |

Render blocks outbound SMTP connections on port 587, which is why you were getting timeout errors. The HTTP API uses standard HTTPS (port 443) which is never blocked.

---

## 🐛 Troubleshooting

### If emails aren't sending:

1. **Check Render logs** for:
   ```
   ✅ Brevo API configured - using HTTP API (no SMTP)
   ```

2. **Verify the API key** is set correctly:
   - Should start with `xkeysib-`
   - Should be the **API Key**, not SMTP key

3. **Check Brevo dashboard** → **Logs** → **Email Logs** for delivery status

4. **Ensure sender email is verified** in Brevo (meghmodi4ever@gmail.com)

5. **Check spam folder** - first emails might go to spam

### Common Issues:

- ❌ **"ApiException: Unauthorized"**: Wrong API key or expired key
- ❌ **"Sender not verified"**: Add and verify your sender email in Brevo
- ❌ **"SDK not installed"**: Run `pip install sib-api-v3-sdk` (already in requirements.txt)
- ❌ **No emails sent**: BREVO_API_KEY environment variable not set in Render

---

## 🎯 What Changed

1. ✅ **Switched from SMTP to HTTP API** (no more port blocking!)
2. ✅ **Added custom email backend** (`core.brevo_backend.BrevoEmailBackend`)
3. ✅ **Added Brevo SDK** to requirements.txt (`sib-api-v3-sdk`)
4. ✅ **Simplified environment variables** (only need `BREVO_API_KEY` now)

---

## 📝 Environment Variables Summary

Make sure you have these in Render:

| Variable | Value Example | Required |
|----------|---------------|----------|
| `ENV` | `render` | ✅ Yes |
| `BREVO_API_KEY` | `xkeysib-abc123...` | ✅ Yes |
| `FROM_EMAIL` | `meghmodi4ever@gmail.com` | ✅ Yes |
| `DB_NAME` | (your PostgreSQL name) | ✅ Yes |
| `DB_USER` | (your PostgreSQL user) | ✅ Yes |
| `DB_PASSWORD` | (your PostgreSQL password) | ✅ Yes |
| `DB_HOST` | (your PostgreSQL host) | ✅ Yes |
| `DB_PORT` | `5432` | ✅ Yes |

---

## 🔗 Useful Links

- Brevo Dashboard: https://app.brevo.com/
- Brevo API Keys: https://app.brevo.com/settings/keys/api
- Brevo API Documentation: https://developers.brevo.com/docs
- Email Logs: https://app.brevo.com/log

---

## 📈 Brevo Free Tier Benefits

- **300 emails per day** (vs 100 with SendGrid)
- Unlimited contacts
- Email templates
- Real-time statistics
- **HTTP API works on ALL cloud platforms** (no SMTP blocking)

---

**That's it! Your email system will now work perfectly on Render! 🎉**

**No more timeout errors - HTTP API bypasses all SMTP port blocking issues!**
