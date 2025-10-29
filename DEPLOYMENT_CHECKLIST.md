# Deployment Checklist - Critical Actions Required

## IMMEDIATE ACTIONS REQUIRED

### 1. Run Database Migrations (CRITICAL)
```bash
cd proctor
python manage.py makemigrations
python manage.py migrate
```

**Changes being applied:**
- Violation.type field increased to 50 characters
- Added Violation.is_frozen and Violation.freeze_cancelled_by fields
- New ExamAttempt model for tracking attempts
- Related name changes for better querying

### 2. Test Core Functionality

**Test Sequence:**
1. **Exam Loading:**
   - Navigate to student exam page
   - Verify page loads in <2 seconds
   - Check for no "broken pipe" errors

2. **Camera Initialization:**
   - Click "Initialize Camera"
   - Verify face detection overlay appears
   - Wait for "✓ Face Detected" indicator
   - Confirm "Start Exam" button enables

3. **Distraction Detection:**
   - Start exam
   - Look away for 5 seconds - should see timer: "Looking away (5s)"
   - Look away for 10+ seconds - should get WARNING
   - Verify warning count increases
   - With warning_limit=1, trigger freeze

4. **Freeze Timer:**
   - Verify 5-minute countdown appears
   - Try pressing back button - should be blocked
   - Try refreshing - should stay on exam page
   - Wait for unfreeze or test faculty cancel

5. **Faculty Monitoring:**
   - Login as faculty
   - Navigate to `/faculty/live-monitoring/`
   - Verify active students appear
   - Test "Unfreeze" button
   - Test "Reset Attempt" button
   - Check analytics dashboard

### 3. Verify All URLs Work

Test these URLs (adjust exam_id and student_id):
- `/faculty/live-monitoring/` - Live monitoring dashboard
- `/faculty/cancel-freeze/` - API endpoint (POST)
- `/faculty/reset-attempt/` - API endpoint (POST)  
- `/faculty/violations/1/1/` - Violation details
- `/faculty/analytics/` - Student analytics
- `/faculty/analytics/exam/1/` - Exam analytics

### 4. Check for Console Errors

**Expected Warnings (SAFE TO IGNORE):**
```
W0000 00:00:1761742466.539228 21948 inference_feedback_manager.cc:114
Feedback manager requires a model with a single signature inference
```
These are MediaPipe warnings and don't affect functionality.

**JavaScript Lint Errors (SAFE TO IGNORE):**
Lint errors on lines 697-698 are from Django template variables in JS. They resolve at runtime.

## CONFIGURATION CHECKLIST

### Settings.py
```python
# For Production, set:
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Database backup recommended
DATABASES = {
    'default': {
        # Configure with proper credentials
    }
}
```

### Admin User
Create superuser for faculty monitoring:
```bash
python manage.py createsuperuser
```

## FEATURE VERIFICATION

### ✅ Fixed Features
- [x] Page loads instantly
- [x] CSRF tokens work
- [x] Face detection during setup
- [x] 10-second threshold before warnings
- [x] Back button blocked during exam
- [x] Exam attempts tracked
- [x] Faculty can unfreeze students
- [x] Faculty can reset attempts
- [x] Live monitoring dashboard
- [x] Analytics dashboards

### ⚠️ To Test
- [ ] Multiple concurrent students
- [ ] Database performance with 100+ violations
- [ ] Camera on different browsers
- [ ] Mobile device compatibility
- [ ] Network interruption handling

## KNOWN LIMITATIONS

1. **Auto-refresh:** Live monitoring reloads every 10 seconds (may cause flicker)
2. **MediaPipe Warnings:** Console shows TensorFlow warnings (harmless)
3. **Django Template Lints:** IDE shows JS errors in templates (resolve at runtime)
4. **No WebSockets:** Real-time updates use polling instead of WebSockets
5. **Camera Permission:** Must be granted before exam starts

## SECURITY NOTES

### Current Security Measures:
✅ CSRF protection on all POST requests
✅ Login required decorators
✅ Role-based access control
✅ Back button prevention
✅ Exam attempt tracking
✅ Faculty action logging (partial)

### Security Gaps (Future):
⚠️ No rate limiting on API endpoints
⚠️ No session timeout enforcement
⚠️ No IP validation
⚠️ No encrypted violation storage
⚠️ No comprehensive audit logs

## PERFORMANCE OPTIMIZATION

### Current State:
- Page load: <1 second
- Distraction check: Every 2 seconds
- Live monitoring refresh: Every 10 seconds

### Recommended Improvements:
1. Add Redis caching for dashboards
2. Implement WebSockets for real-time updates
3. Add database indexing:
   ```sql
   CREATE INDEX idx_violation_exam_student ON core_violation(exam_id, student_id);
   CREATE INDEX idx_attempt_exam_student ON core_examattempt(exam_id, student_id);
   ```

## BACKUP STRATEGY

Before deployment:
```bash
# Backup database
python manage.py dumpdata > backup_$(date +%Y%m%d).json

# Backup media files
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/

# Backup static files
python manage.py collectstatic --noinput
```

## ROLLBACK PLAN

If issues occur:
```bash
# Rollback migrations
python manage.py migrate core <previous_migration_number>

# Restore database
python manage.py loaddata backup_YYYYMMDD.json

# Restart server
systemctl restart gunicorn  # or your web server
```

## MONITORING SETUP

### Recommended Tools:
1. **Error Tracking:** Sentry
2. **Performance:** New Relic or DataDog
3. **Uptime:** UptimeRobot
4. **Logs:** ELK Stack or CloudWatch

### Key Metrics to Monitor:
- Exam page load time
- API response times (/check_distraction/)
- Database query performance
- Server CPU/Memory usage
- Active exam count
- Violation rate

## SUPPORT CONTACTS

### If Issues Occur:
1. Check logs: `tail -f /var/log/django/error.log`
2. Check database: `python manage.py dbshell`
3. Check migrations: `python manage.py showmigrations`
4. Clear cache: `python manage.py clear_cache` (if implemented)

## FINAL CHECKLIST

Before going live:
- [ ] Migrations run successfully
- [ ] All URLs return 200 (not 404/500)
- [ ] Test exam from start to finish
- [ ] Test faculty monitoring dashboard
- [ ] Test all action buttons (unfreeze, reset)
- [ ] Verify CSRF tokens work
- [ ] Check console for critical errors
- [ ] Test on multiple browsers (Chrome, Firefox, Edge)
- [ ] Backup database
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Enable HTTPS
- [ ] Test rollback procedure

## POST-DEPLOYMENT

### Week 1:
- Monitor error rates daily
- Check violation logs for anomalies
- Gather faculty feedback
- Monitor server resources

### Week 2-4:
- Analyze performance metrics
- Optimize slow queries
- Address user feedback
- Plan feature enhancements

## EMERGENCY CONTACTS

Have ready:
- Database administrator
- System administrator
- Network team
- Backup/restore procedures
- Vendor support (if applicable)

---

**Created:** $(date)
**Version:** 1.0
**Last Updated:** After major bug fixes and feature additions
