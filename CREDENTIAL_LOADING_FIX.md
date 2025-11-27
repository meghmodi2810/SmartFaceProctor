# Render Deployment - Credential Loading Fix

## ✅ Changes Made

I've updated your credential loading system to handle missing files gracefully during build time. This prevents the `FileNotFoundError` that was causing your build to fail.

### Files Modified:

1. **`proctor/core/config/__init__.py`** - Updated with fallback mechanisms
2. **`proctor/core/Modules/send_email_using_sheets.py`** - Updated to handle None paths

---

## 🔧 How It Works Now

### During Build (when files don't exist):
- ✅ The system won't crash if credential files are missing
- ✅ Falls back to environment variables for SMTP settings
- ✅ Returns `None` for paths if files don't exist
- ✅ Prints warnings instead of throwing errors

### During Runtime (when files exist):
- ✅ Loads credentials from `/etc/secrets/` on Render
- ✅ Loads from local `config/` folder in development
- ✅ Works exactly as before

---

## 📋 Next Steps for Render Deployment

### Step 1: Upload Secret Files to Render

1. Go to **Render Dashboard** → **Your Web Service**
2. Click on **"Environment"** tab in the left sidebar
3. Scroll down to **"Secret Files"** section
4. Click **"Add Secret File"**

**Add File 1: Google Sheets Credentials**
```
Filename: credentials.json
Content: [Paste your entire Google Service Account JSON here]
```

**Add File 2: SMTP Credentials**
```
Filename: SMTP_credentials.json
Content: [Paste your SMTP credentials JSON here]
```

Example SMTP JSON format:
```json
{
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": 465,
    "SMTP_USER": "your-email@gmail.com",
    "SMTP_API_KEY": "your-app-password",
    "FROM_EMAIL": "your-email@gmail.com"
}
```

### Step 2: Set Environment Variables on Render

Go to **Environment** tab → **Environment Variables** section:

| Key | Value |
|-----|-------|
| `RENDER` | `true` |
| `GOOGLE_SHEETS_CRED` | `/etc/secrets/credentials.json` |
| `SMTP_CRED` | `/etc/secrets/SMTP_credentials.json` |

**Optional (Fallback during build):**
| Key | Value | Purpose |
|-----|-------|---------|
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_HOST_USER` | `your-email@gmail.com` | Your email |
| `EMAIL_HOST_PASSWORD` | `your-app-password` | Your app password |
| `EMAIL_FROM` | `your-email@gmail.com` | From email |
| `EMAIL_USE_TLS` | `True` | Use TLS |

### Step 3: Verify Your Start Command

Make sure your **Start Command** in Render is:
```bash
cd proctor && gunicorn proctor.wsgi:application --bind 0.0.0.0:$PORT
```

### Step 4: Commit and Deploy

1. Commit your changes:
```bash
git add .
git commit -m "Fix credential loading for Render deployment"
git push origin main
```

2. **Render will automatically deploy** OR click "Manual Deploy" in Render dashboard

---

## 🎯 What This Fix Does

### Before (❌ Failed):
```
Build Process:
1. Install packages ✅
2. Collect static files
   └─ Django tries to import core.admin
      └─ core.admin imports core.config
         └─ core.config tries to read /etc/secrets/SMTP_credentials.json
            └─ ❌ File doesn't exist during build
               └─ ❌ BUILD FAILS
```

### After (✅ Success):
```
Build Process:
1. Install packages ✅
2. Collect static files
   └─ Django tries to import core.admin
      └─ core.admin imports core.config
         └─ core.config checks if file exists
            └─ File not found? Use fallback (empty dict or env vars)
               └─ ✅ BUILD CONTINUES
3. Run migrations ✅
4. Deploy ✅

Runtime:
1. User visits site
2. Secret files ARE available in /etc/secrets/
3. Credentials load successfully ✅
4. Everything works! ✅
```

---

## 🔍 Testing Locally

Your local development is **not affected** by these changes. It will still work exactly as before because:

1. Local files are still in `proctor/core/config/`
2. `RENDER` environment variable is not set locally
3. The code detects local environment and uses local paths

---

## 🚨 Troubleshooting

### If build still fails:

1. **Check your `build.sh` file is correct:**
```bash
#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

cd proctor

python manage.py collectstatic --no-input
python manage.py migrate
```

2. **Verify the file is executable** (Render should handle this automatically)

3. **Check Render logs** for specific error messages

### If deployment succeeds but emails don't work:

1. Verify secret files were uploaded correctly in Render dashboard
2. Check environment variables are set correctly
3. Look at runtime logs for credential loading warnings

---

## 📚 Additional Notes

- **Secret files** are only available at **runtime**, not during **build time**
- This is why we need the fallback mechanism
- Environment variables are available at both build and runtime
- Your local development remains unchanged

---

## ✅ Deployment Checklist

- [ ] Updated `core/config/__init__.py` (✅ Done)
- [ ] Updated `send_email_using_sheets.py` (✅ Done)
- [ ] Committed and pushed changes to GitHub
- [ ] Uploaded `credentials.json` as secret file in Render
- [ ] Uploaded `SMTP_credentials.json` as secret file in Render
- [ ] Set `RENDER=true` environment variable
- [ ] Set `GOOGLE_SHEETS_CRED` environment variable
- [ ] Set `SMTP_CRED` environment variable
- [ ] Verified Start Command is correct
- [ ] Triggered deployment on Render
- [ ] Checked deployment logs for success
- [ ] Tested the application is working

---

**You're now ready to deploy! 🚀**
