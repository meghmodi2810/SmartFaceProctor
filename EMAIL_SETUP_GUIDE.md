# Email Notification Setup Guide

This guide explains how to configure email notifications for the Smart Face Proctor System.

## 📧 Email Notifications

The system automatically sends email notifications for:

### 1. **New Exam Scheduled** 
- Triggered when faculty creates a new exam
- Sent to all eligible students
- For selective exams: only assigned students receive notification
- For general exams: all students receive notification

### 2. **Exam Results Available**
- Triggered when faculty grades an exam (Submission is created)
- Sent to individual student with their score and grade
- Includes pass/fail status

### 3. **Selective Exam Assignment**
- Triggered when a student is assigned to a selective exam
- Sent to the newly assigned student

---

## ⚙️ SMTP Configuration

### Step 1: Edit `settings.py`

Open `proctor/proctor/settings.py` and configure the email settings (lines 201-214):

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Your SMTP server
EMAIL_PORT = 587  # TLS port
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'your-email@gmail.com'  # Your email address
EMAIL_HOST_PASSWORD = 'your-app-password'  # Your app-specific password
DEFAULT_FROM_EMAIL = 'Smart Face Proctor <noreply@proctorsystem.com>'
SITE_URL = 'http://localhost:8000'  # Your site URL
```

---

## 🔐 Gmail Setup (Recommended)

### Option 1: Using Gmail App Password (Recommended)

1. **Enable 2-Step Verification:**
   - Go to: https://myaccount.google.com/security
   - Enable 2-Step Verification

2. **Generate App Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - Select app: "Mail"
   - Select device: "Other" (enter "Django Proctor System")
   - Click "Generate"
   - Copy the 16-character password

3. **Update settings.py:**
   ```python
   EMAIL_HOST_USER = 'your-email@gmail.com'
   EMAIL_HOST_PASSWORD = 'your-16-char-app-password'
   ```

### Option 2: Using Less Secure Apps (Not Recommended)

1. Go to: https://myaccount.google.com/lesssecureapps
2. Turn on "Allow less secure apps"
3. Use your regular Gmail password in settings.py

**Note:** This option is less secure and may be deprecated by Google.

---

## 📮 Other Email Providers

### Microsoft Outlook / Office 365
```python
EMAIL_HOST = 'smtp-mail.outlook.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@outlook.com'
EMAIL_HOST_PASSWORD = 'your-password'
```

### Yahoo Mail
```python
EMAIL_HOST = 'smtp.mail.yahoo.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_HOST_USER = 'your-email@yahoo.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

### Custom SMTP Server
```python
EMAIL_HOST = 'mail.yourdomain.com'
EMAIL_PORT = 587  # or 465 for SSL
EMAIL_USE_TLS = True  # or False if using SSL
EMAIL_HOST_USER = 'noreply@yourdomain.com'
EMAIL_HOST_PASSWORD = 'your-password'
```

---

## 🧪 Testing Email Configuration

### Test from Django Shell

```bash
python manage.py shell
```

```python
from django.core.mail import send_mail

send_mail(
    'Test Email',
    'This is a test email from Smart Face Proctor System.',
    'noreply@proctorsystem.com',
    ['student-email@example.com'],
    fail_silently=False,
)
```

If successful, you'll see: `1` (number of emails sent)

---

## 📁 Email Templates

Emails use professional HTML templates with:
- Beautiful gradient headers
- Responsive design
- Color-coded information cards
- Call-to-action buttons
- Plain text fallback

### Customizing Email Templates

Email templates are generated in `core/email_notifications.py`:
- `send_exam_scheduled_notification()` - New exam notifications
- `send_exam_result_notification()` - Result notifications

---

## 🔔 Signal Handlers

Email notifications are triggered automatically using Django signals in `core/signals.py`:

### 1. `notify_students_on_exam_creation`
- **Trigger:** When `Exam` object is created
- **Action:** Sends email to all eligible students

### 2. `notify_student_on_selective_assignment`
- **Trigger:** When `ExamAssignment` is created
- **Action:** Sends email to newly assigned student

### 3. `notify_student_on_result_available`
- **Trigger:** When `Submission` is created
- **Action:** Sends result email to student

---

## 🚨 Troubleshooting

### Problem: Emails not sending

**Check 1: SMTP Credentials**
```python
# Verify in settings.py
print(settings.EMAIL_HOST_USER)
print(settings.EMAIL_HOST_PASSWORD)  # Should not be empty
```

**Check 2: Firewall/Port**
- Ensure port 587 (TLS) or 465 (SSL) is not blocked
- Try telnet test: `telnet smtp.gmail.com 587`

**Check 3: Django Logs**
```bash
# Check logs/exam_monitoring.log for email errors
tail -f logs/exam_monitoring.log
```

### Problem: Gmail blocks sign-in

**Solution:**
1. Use App Password instead of regular password
2. Check: https://accounts.google.com/DisplayUnlockCaptcha
3. Try signing in from the same IP address

### Problem: Emails go to spam

**Solution:**
1. Add proper SPF/DKIM records if using custom domain
2. Use verified "From" email address
3. Ask recipients to whitelist the sender

---

## 🔒 Security Best Practices

1. **Never commit credentials to Git:**
   ```bash
   # Add to .gitignore
   .env
   ```

2. **Use environment variables:**
   ```python
   # settings.py
   import os
   EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
   EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
   ```

3. **Use App Passwords instead of account passwords**

4. **Rotate passwords regularly**

---

## 📊 Email Notification Features

### New Exam Email Includes:
- Exam title and description
- Date and time
- Duration
- Faculty name
- Important reminders
- Direct link to student dashboard

### Result Email Includes:
- Pass/Fail status with color coding
- Score percentage
- Letter grade (O, A, B, C, F)
- Exam details
- Submission timestamp
- Link to view all results

---

## 🎯 Production Deployment

For production, update:

```python
# In settings.py
SITE_URL = 'https://yourproductionurl.com'
DEFAULT_FROM_EMAIL = 'Smart Face Proctor <noreply@yourdomain.com>'
```

Consider using dedicated email services:
- SendGrid
- Amazon SES
- Mailgun
- PostMark

These provide better deliverability and analytics.

---

## 📝 Email Sending Scenarios

| Event | Trigger | Recipients | Template |
|-------|---------|-----------|----------|
| Exam Created (General) | Faculty schedules exam for all | All active students | Exam Scheduled |
| Exam Created (Selective) | Faculty schedules selective exam | No one (until assigned) | - |
| Student Assigned | Faculty assigns student to selective exam | Assigned student | Exam Scheduled |
| Result Published | Faculty submits grade | Individual student | Exam Result |

---

## Need Help?

Check the logs at `logs/exam_monitoring.log` for detailed error messages.
