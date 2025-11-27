# Render Deployment Guide - Credentials Configuration

## ✅ Changes Implemented

All credential files now support both **local development** and **Render production** environments automatically.

### Files Modified:
1. ✅ `proctor/core/config/__init__.py` - **NEW** centralized config module
2. ✅ `proctor/core/Modules/send_email_using_sheets.py` - Updated to use centralized config
3. ✅ `proctor/core/admin.py` - Updated to use centralized config
4. ✅ `proctor/core/Modules/ExamValidationModule.py` - Updated to use centralized config
5. ✅ `proctor/core/Modules/SheetManagerModule.py` - Updated to use centralized config

---

## 🚀 Render Deployment Setup

### Step 1: Upload Secret Files to Render

1. Go to your Render Dashboard
2. Select your web service
3. Go to **"Environment"** tab
4. Scroll down to **"Secret Files"** section
5. Add two secret files:

   **File 1: Google Sheets Credentials**
   - Filename: `credentials.json`
   - Content: Paste your entire Google Service Account JSON

   **File 2: SMTP Credentials**
   - Filename: `SMTP_credentials.json`
   - Content: Paste your SMTP configuration JSON

### Step 2: Set Environment Variables on Render

Go to **"Environment Variables"** section and add these:

| Variable Name | Value |
|--------------|-------|
| `RENDER` | `true` |
| `GOOGLE_SHEETS_CRED` | `/etc/secrets/credentials.json` |
| `SMTP_CRED` | `/etc/secrets/SMTP_credentials.json` |

### Step 3: Verify .gitignore

Make sure these files are already in `.gitignore` (they are):
```
proctor/core/config/credentials.json
proctor/core/config/SMTP_credentials.json
```

---

## 💻 Local Development

**No changes needed!** The system automatically detects when running locally and uses:
- `proctor/core/config/credentials.json` (for Google Sheets)
- `proctor/core/config/SMTP_credentials.json` (for SMTP)

Keep your local credential files in the `proctor/core/config/` folder as before.

---

## 🔍 How It Works

The new `proctor/core/config/__init__.py` module:

1. **Detects Environment**: Checks if `RENDER` environment variable is `true`
2. **Loads Credentials**:
   - **On Render**: Uses paths from environment variables → `/etc/secrets/`
   - **Locally**: Uses local JSON files in `config/` folder
3. **Provides Easy Access**: All modules import from centralized config

### Example Usage:
```python
from core.config import smtp_credentials_path, google_credentials_path

# Automatically points to correct path based on environment
# - Render: /etc/secrets/SMTP_credentials.json
# - Local: proctor/core/config/SMTP_credentials.json
```

---

## ✅ Testing Checklist

### Before Deploying to Render:
- [ ] Verify local credentials are in `proctor/core/config/` folder
- [ ] Test locally that app still works
- [ ] Commit changes to Git
- [ ] Push to GitHub/repository

### After Deploying to Render:
- [ ] Upload both secret files (`credentials.json` and `SMTP_credentials.json`)
- [ ] Set all 3 environment variables (`RENDER`, `GOOGLE_SHEETS_CRED`, `SMTP_CRED`)
- [ ] Trigger manual deploy or push changes
- [ ] Test exam creation (uses Google Sheets API)
- [ ] Test sending emails (uses SMTP)
- [ ] Check logs for any credential-related errors

---

## 🛠️ Troubleshooting

### If credentials not loading on Render:

1. **Check Environment Variables** are set exactly as:
   ```
   RENDER=true
   GOOGLE_SHEETS_CRED=/etc/secrets/credentials.json
   SMTP_CRED=/etc/secrets/SMTP_credentials.json
   ```

2. **Verify Secret Files** are uploaded correctly in Render dashboard

3. **Check Logs** in Render dashboard for any file not found errors

4. **Restart Service** after adding environment variables

### If it works locally but not on Render:

- Ensure `RENDER=true` (case-sensitive, lowercase "true")
- Verify secret files have correct JSON format
- Check Render build logs for any import errors

---

## 📋 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RENDER` | Yes | - | Set to `true` to enable Render mode |
| `GOOGLE_SHEETS_CRED` | Yes* | `/etc/secrets/credentials.json` | Path to Google credentials |
| `SMTP_CRED` | Yes* | `/etc/secrets/SMTP_credentials.json` | Path to SMTP credentials |

*Required only when `RENDER=true`

---

## 🎉 Summary

Your project is now **production-ready** with automatic environment detection:

- ✅ Works seamlessly in both local and production environments
- ✅ No code changes needed when switching environments
- ✅ Credentials secured using Render's secret files
- ✅ Environment variables control paths
- ✅ All modules updated to use centralized configuration

**Next Step**: Deploy to Render and follow the testing checklist above!
