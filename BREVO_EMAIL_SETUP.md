# 📧 Brevo (Sendinblue) Email Setup Guide

## ✅ Configuration Complete!

Your application is now configured to use **Brevo SMTP** for sending emails in production.

---

## 🔑 Step 1: Get Your Brevo SMTP Credentials

1. **Login to Brevo**: https://app.brevo.com/
2. Go to **Settings** → **SMTP & API**
3. Under **SMTP** section, you'll find:
   - **SMTP Server**: `smtp-relay.brevo.com`
   - **Port**: `587`
   - **Login**: Your Brevo account email (e.g., `meghmodi4ever@gmail.com`)
   - **SMTP Key**: Click "Create a new SMTP key" if you don't have one

---

## 🚀 Step 2: Add Environment Variables to Render

Go to your Render Dashboard → Your Web Service → **Environment** tab and add these variables:

```
BREVO_SMTP_USER=your-brevo-login-email@gmail.com
BREVO_SMTP_KEY=your-brevo-smtp-key-here
FROM_EMAIL=meghmodi4ever@gmail.com
```

**Important Notes:**
- `BREVO_SMTP_USER` is your Brevo account email (the one you use to login)
- `BREVO_SMTP_KEY` is the SMTP API key you generated (NOT your account password)
- `FROM_EMAIL` must be a verified sender in Brevo

---

## ✉️ Step 3: Verify Your Sender Email in Brevo

1. Go to **Senders** in Brevo dashboard
2. Click **Add a Sender**
3. Add your email: `meghmodi4ever@gmail.com`
4. Verify it by clicking the link in the verification email
5. Wait for approval (usually instant for Gmail addresses)

---

## 🧪 Step 4: Test Email Sending

After deploying to Render with the environment variables:

1. Try the **Forgot Password** feature
2. Check Brevo dashboard → **Statistics** → **Email Activity** to see if emails are being sent
3. Check your server logs in Render for email debug info

---

## 📊 Brevo Free Tier Limits

- **300 emails per day** (much better than SendGrid's 100!)
- Unlimited contacts
- Email templates
- Real-time statistics

---

## 🐛 Troubleshooting

### If emails aren't sending:

1. **Check Render logs** for email configuration printout:
   ```
   📧 EMAIL CONFIGURATION (RENDER/BREVO)
   ```

2. **Verify environment variables** are set correctly in Render

3. **Check Brevo dashboard** → Email Activity for delivery status

4. **Ensure sender email is verified** in Brevo

5. **Check spam folder** - first emails might go to spam

### Common Issues:

- ❌ **"Authentication failed"**: Wrong SMTP key or username
- ❌ **"Sender not verified"**: Add and verify your sender email in Brevo
- ❌ **No emails sent**: Environment variables not set in Render
- ❌ **Timeout errors**: Network issue, check Render logs

---

## 🎯 What Changed in Your Code

1. **Email Host**: Changed from `smtp.sendgrid.net` → `smtp-relay.brevo.com`
2. **Environment Variables**: 
   - `SENDGRID_API_KEY` → `BREVO_SMTP_KEY`
   - Added `BREVO_SMTP_USER`
3. **Free Tier**: 100 emails/day → 300 emails/day ✅

---

## 📝 Next Steps

1. ✅ Copy your Brevo SMTP credentials
2. ✅ Add environment variables to Render
3. ✅ Verify sender email in Brevo
4. ✅ Deploy your code to Render
5. ✅ Test password reset or registration

---

## 🔗 Useful Links

- Brevo Dashboard: https://app.brevo.com/
- Brevo SMTP Settings: https://app.brevo.com/settings/keys/smtp
- Brevo Documentation: https://developers.brevo.com/docs

---

**That's it! Your email system is now configured with Brevo SMTP! 🎉**
