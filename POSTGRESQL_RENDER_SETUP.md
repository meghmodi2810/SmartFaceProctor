# PostgreSQL Database Setup for Render Deployment

## ✅ Changes Completed

1. **Updated `settings.py`**: Now uses PostgreSQL for production (Render) and MySQL for local development
2. **Updated `requirements.txt`**: Added `psycopg2-binary==2.9.9` for PostgreSQL support

---

## 🗄️ Step-by-Step: Create PostgreSQL Database on Render

### Step 1: Create PostgreSQL Database

1. Go to **Render Dashboard** → https://dashboard.render.com
2. Click **"New +"** button (top right)
3. Select **"PostgreSQL"**
4. Fill in the form:
   - **Name**: `proctor-db` (or any name you prefer)
   - **Database**: `proctor_db`
   - **User**: `proctor_user`
   - **Region**: **Same region as your web service** (e.g., Oregon)
   - **PostgreSQL Version**: `16` (latest)
   - **Plan**: **Free** (starts at $0/month)
5. Click **"Create Database"**
6. Wait 1-2 minutes for provisioning

### Step 2: Get Database Connection Details

Once the database is created:

1. Click on your newly created database (`proctor-db`)
2. You'll see the **Connections** section with:
   - **Internal Database URL** - Use this for your web service
   - **External Database URL** - Use this for local connections (optional)
   
3. **Copy the Internal Database URL** - It looks like:
   ```
   postgresql://proctor_user:LONG_PASSWORD_HERE@dpg-xxxxx-a/proctor_db
   ```

4. You'll also see individual connection parameters:
   - **Hostname**: `dpg-xxxxx-a` (internal hostname)
   - **Port**: `5432`
   - **Database**: `proctor_db`
   - **Username**: `proctor_user`
   - **Password**: `[long random string]`

---

## ⚙️ Step 3: Configure Web Service Environment Variables

### Option A: Use DATABASE_URL (Recommended - Simpler)

Go to your **Web Service** → **Environment** → **Environment Variables**:

Add these variables:

| Key | Value |
|-----|-------|
| `ENV` | `render` |
| `DATABASE_URL` | `[Paste Internal Database URL here]` |

Then update your `settings.py` to use `DATABASE_URL`:

```python
import os
import dj_database_url

ENV = os.environ.get("ENV", "local")

if ENV != 'render':
    # Local development - MySQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'proctor_db',
            'USER': 'root',
            'PASSWORD': '6640',
            'HOST': 'localhost',
            'PORT': '3306',
        }
    }
else:
    # Production on Render - PostgreSQL
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600
        )
    }
```

**Note**: If using this option, add `dj-database-url==2.1.0` to `requirements.txt`

### Option B: Use Individual Variables (Current Setup)

Go to your **Web Service** → **Environment** → **Environment Variables**:

| Key | Value | Example |
|-----|-------|---------|
| `ENV` | `render` | `render` |
| `DB_NAME` | Database name | `proctor_db` |
| `DB_USER` | Username | `proctor_user` |
| `DB_PASSWORD` | Password from Render | `xyz123abc456...` |
| `DB_HOST` | Internal hostname | `dpg-xxxxx-a` |
| `DB_PORT` | Port number | `5432` |

---

## 🔗 Step 4: Link Database to Web Service

### Automatic Linking (Recommended):

1. In your **Web Service** settings
2. Scroll to **"Environment Variables"**
3. Click **"Add from Database"**
4. Select your `proctor-db` database
5. Render will automatically add `DATABASE_URL`

### Manual Linking:

Just copy the **Internal Database URL** from your PostgreSQL database and paste it as the `DATABASE_URL` environment variable.

---

## 📝 Step 5: Update Your Build Script

Your `build.sh` should already work, but verify it looks like this:

```bash
#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

cd proctor

python manage.py collectstatic --no-input
python manage.py migrate
```

---

## 🚀 Step 6: Deploy

1. **Commit and push your changes:**
   ```bash
   git add .
   git commit -m "Add PostgreSQL support for Render deployment"
   git push origin main
   ```

2. Render will automatically deploy, or click **"Manual Deploy"**

3. **Watch the build logs** - You should see:
   ```
   ✅ Installing packages...
   ✅ Collecting static files...
   ✅ Running migrations...
   ✅ Build successful 🎉
   ✅ Deploying...
   ✅ Running gunicorn...
   ✅ Service is live 🎉
   ```

---

## 🔍 Verify Database Connection

After deployment succeeds, verify the database connection:

1. Go to **Render Dashboard** → **Your Web Service** → **Shell**
2. Run:
   ```bash
   cd proctor
   python manage.py dbshell
   ```
3. If connected successfully, you'll see PostgreSQL prompt:
   ```
   psycopg2.connect()
   proctor_db=>
   ```
4. Type `\dt` to see tables, `\q` to quit

---

## 🎯 Environment Variable Summary

### Required Variables for Render:

| Variable | Value | Purpose |
|----------|-------|---------|
| `RENDER` | `true` | Detect Render environment |
| `ENV` | `render` | Database switching |
| `GOOGLE_SHEETS_CRED` | `/etc/secrets/credentials.json` | Google API |
| `SMTP_CRED` | `/etc/secrets/SMTP_credentials.json` | Email |
| `DATABASE_URL` | `postgresql://...` | Database connection |

### Optional (if not using DATABASE_URL):

| Variable | Value |
|----------|-------|
| `DB_NAME` | `proctor_db` |
| `DB_USER` | `proctor_user` |
| `DB_PASSWORD` | `[from Render]` |
| `DB_HOST` | `dpg-xxxxx-a` |
| `DB_PORT` | `5432` |

---

## 📊 Database Migration from MySQL to PostgreSQL (Optional)

If you have existing data in MySQL that you want to migrate:

### Method 1: Using Django's dumpdata/loaddata

**On local (MySQL):**
```bash
cd proctor
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > data.json
```

**On Render (PostgreSQL):**
```bash
# Upload data.json to your repo
cd proctor
python manage.py loaddata data.json
```

### Method 2: Manual Export/Import

Use tools like:
- **pgloader** - Automated migration tool
- **Django fixtures** - Export/import JSON data
- **Custom migration scripts** - Write Python scripts

---

## 🧪 Testing Locally with PostgreSQL (Optional)

If you want to test with PostgreSQL locally before deploying:

1. **Install PostgreSQL** on your machine
2. **Create local database:**
   ```sql
   CREATE DATABASE proctor_db;
   CREATE USER proctor_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE proctor_db TO proctor_user;
   ```

3. **Update your local settings temporarily:**
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'proctor_db',
           'USER': 'proctor_user',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

---

## 🚨 Troubleshooting

### Error: "psycopg2 not found"
**Solution**: Make sure `psycopg2-binary==2.9.9` is in your `requirements.txt`

### Error: "connection refused"
**Solution**: 
- Verify `DATABASE_URL` or individual DB variables are correct
- Check that web service and database are in the same region
- Use **Internal Database URL**, not External

### Error: "SSL required"
**Solution**: Add to settings.py:
```python
if ENV == 'render':
    DATABASES['default']['OPTIONS'] = {
        'sslmode': 'require',
    }
```

### Migrations not running
**Solution**: Check `build.sh` includes:
```bash
python manage.py migrate
```

---

## ✅ Deployment Checklist

- [x] Created PostgreSQL database on Render
- [x] Updated `settings.py` to use PostgreSQL for production
- [x] Added `psycopg2-binary` to `requirements.txt`
- [ ] Set `ENV=render` environment variable
- [ ] Set `DATABASE_URL` environment variable (or individual DB vars)
- [ ] Uploaded secret files (credentials.json, SMTP_credentials.json)
- [ ] Set SMTP and Google Sheets environment variables
- [ ] Committed and pushed changes
- [ ] Triggered deployment
- [ ] Verified build succeeds
- [ ] Tested application is working
- [ ] Verified database connection

---

**Your application is now configured for PostgreSQL on Render! 🎉**
