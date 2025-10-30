# Testing Guide - Smart Face Proctor System

## Quick Testing Checklist

### ✅ Test 1: Admin Panel Navigation (30 seconds)
```
1. Login as Admin: http://localhost:8000/customadmin/
2. Check left sidebar - Should see:
   ├── Departments
   ├──── Semesters (indented)
   └──── Divisions (indented)
3. Click each link - all pages should load
```

**Expected Result:** All three pages accessible and functional

---

### ✅ Test 2: Create Division & Semester (2 minutes)

**Step A: Create Semester**
```
1. Admin Panel → Semesters
2. Select a Department from dropdown
3. Click "Add Semester" button
4. Enter name: "Semester 1"
5. Click Submit
```
**Expected:** Semester created successfully

**Step B: Create Division**
```
1. Admin Panel → Divisions
2. Select a Department from dropdown
3. Optionally select a Semester
4. Click "Add Division" button
5. Enter name: "Division A"
6. Click Submit
```
**Expected:** Division created successfully

---

### ✅ Test 3: Schedule Exam with Department Selection (3 minutes)

```
1. Login as Faculty
2. Dashboard → Schedule Exam
3. Fill in exam details:
   - Exam Name: "Test Exam"
   - Date & Time: Future date
   - Duration: 60 minutes
   - Google Sheet URL: (your sheet)
4. Student Selection → Select "Select by Department"
5. Choose one or more departments
6. Click Preview → Confirm
```

**Expected:** Exam scheduled, only students in selected departments can see it

---

### ✅ Test 4: Exam Visibility (1 minute)

```
1. Login as Student (from selected department)
2. Go to Dashboard → My Exams
3. Check if exam appears in list
4. Login as Student (from different department)
5. Check exams list
```

**Expected:** 
- Students in selected department see the exam
- Students in other departments don't see it
- If exam was scheduled for "All Students", everyone sees it

---

### ✅ Test 5: Distraction Detection During Exam (5 minutes)

**CRITICAL TEST**

```
1. Login as Student
2. Start an exam that is currently ongoing
3. Camera initialization:
   - Allow camera access
   - Face detection should work (green status)
   - Click "Start Exam"
4. During exam:
   - Answer 1-2 questions
   - Look away from screen for 15 seconds
   - Wait and observe
```

**Expected Results:**
- ✅ After 10 seconds: Warning appears "Looking away from screen (10s)"
- ✅ Warning counter shows: "1 / 3"
- ✅ Notification pops up with warning message
- ✅ Status changes to warning (yellow)

**Continue Test:**
```
5. Look back at screen briefly
6. Look away again for 15 seconds
7. Repeat one more time (total 3 warnings)
```

**Expected After 3rd Warning:**
- ✅ Exam FREEZES immediately
- ✅ Big red overlay appears: "Exam Frozen - 5 Minutes"
- ✅ Countdown timer shows: "4:59, 4:58, 4:57..."
- ✅ All question inputs are DISABLED
- ✅ Submit button is DISABLED
- ✅ Cannot answer any questions

**Browser Console Verification:**
```javascript
// Open browser console (F12)
// You should see logs every 2 seconds:
"Distraction detection started"
"Warning count: 1"
"Warning count: 2"
"Warning count: 3"
"EXAM FROZEN"
```

---

### ✅ Test 6: Submit Exam & View Results (2 minutes)

```
1. Student completes exam (answer all questions)
2. Submit button should be ENABLED when all answered
3. Click "Submit Exam"
4. Observe:
   - Button text changes to "Submitting..." with spinner
   - Wait 1-2 seconds
5. Should redirect to Results Page
```

**Expected Results Page:**
- ✅ Exam title displayed
- ✅ Your Score: X% (e.g., "85%")
- ✅ Correct Answers: Y/Z (e.g., "17/20")
- ✅ Submission timestamp
- ✅ "View Detailed Results" button (if available)

**Database Verification (Optional):**
```
Admin Panel → Submissions
- Find student's submission
- Verify score is saved
- Verify timestamp is correct

Admin Panel → Exam Attempts
- Find student's attempt
- Verify is_active = False
- Verify ended_at has timestamp
```

---

### ✅ Test 7: Faculty Live Monitoring (2 minutes)

```
1. Login as Faculty
2. Dashboard → Live Monitoring
3. While student is taking exam, check:
   - Student name appears in list
   - Warning count shows correctly
   - Violations list updates in real-time
4. If student is frozen:
   - "Frozen" badge appears
   - "Cancel Freeze" button visible
   - Click "Cancel Freeze"
```

**Expected:**
- ✅ Student's freeze is cancelled immediately
- ✅ Student can resume exam
- ✅ Warning count preserved

---

## 🔍 Troubleshooting

### Issue: Distraction Detection Not Working

**Check 1: Browser Console**
```javascript
// Press F12 → Console tab
// Look for errors like:
"Cannot access camera"
"Frame processing failed"
```

**Check 2: Camera Permission**
- Chrome: Click lock icon in address bar → Camera → Allow
- Firefox: Click camera icon in address bar → Allow

**Check 3: Network Tab**
```
F12 → Network tab
Look for requests to /check_distraction/
Status should be 200 OK
Response should have: {face_detected, warning_count, is_frozen}
```

**Check 4: Server Console**
```
Look for Python errors in terminal where server is running
Should see logs like:
"Violation logged: Looking Away, Warning 1/3"
```

### Issue: Submit Button Not Working

**Check 1: All Questions Answered**
- Submit button only enables when ALL questions have answers
- Check counter: "X / Y Answered"

**Check 2: Browser Console**
```javascript
// After clicking submit, check for:
"Error submitting exam: ..."
```

**Check 3: Network Tab**
```
Look for POST to /student/submit-exam/{id}/
Check response:
{success: true, score: 85, correct_count: 17, total_questions: 20}
```

### Issue: Exam Not Visible to Students

**Check 1: Exam Selection Type**
```
Admin → Exams → Find exam → Check is_selective field
- is_selective = False → All students should see it
- is_selective = True → Only assigned students see it
```

**Check 2: Student Assignment**
```
Admin → Exam Assignments
- Look for student_id and exam_id combination
- Verify is_active = True
```

**Check 3: Exam Timing**
```
Check if exam date/time is in the future
Students only see upcoming/ongoing exams
```

---

## 📊 Performance Monitoring

### Check Session State (Developer Tool)

While student is taking exam:
```python
# In Django shell (python manage.py shell)
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='student_username')

# Get sessions
sessions = Session.objects.filter(expire_date__gte=timezone.now())
for session in sessions:
    data = session.get_decoded()
    print(f"Session data: {data}")
    # Look for keys like: detector_{user_id}_{exam_id}
```

### Monitor Database Queries

```python
# Add to settings.py for development:
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

---

## 🎯 Success Criteria

All tests pass if:

✅ **Admin Panel:** Semesters and Divisions are accessible and functional
✅ **Exam Scheduling:** Department-based scheduling works correctly
✅ **Exam Visibility:** Students see correct exams based on assignment
✅ **Distraction Detection:** 
   - Works during camera initialization ✓
   - Works during exam (THIS WAS THE BUG) ✓
   - Accumulates warnings correctly ✓
   - Freezes exam after limit ✓
✅ **Exam Submission:** 
   - Calculates score correctly ✓
   - Shows results page ✓
   - Marks attempt as completed ✓
✅ **Faculty Monitoring:** Real-time updates work correctly

---

## 🚀 Quick Test Script

Save this as `test_system.sh` (Linux/Mac) or `test_system.bat` (Windows):

```bash
#!/bin/bash
echo "🧪 Testing Smart Face Proctor System"
echo "====================================="
echo ""

# Test 1: Server Running
echo "Test 1: Checking if server is running..."
curl -s http://localhost:8000/ > /dev/null && echo "✅ Server is running" || echo "❌ Server is not running"

# Test 2: Admin Panel
echo "Test 2: Checking admin panel..."
curl -s http://localhost:8000/customadmin/ > /dev/null && echo "✅ Admin panel accessible" || echo "❌ Admin panel not accessible"

# Test 3: API Endpoint
echo "Test 3: Checking API endpoints..."
curl -s http://localhost:8000/check_distraction/ > /dev/null && echo "✅ Distraction API accessible" || echo "❌ API not accessible"

echo ""
echo "Manual tests required:"
echo "- Log in and test distraction detection"
echo "- Submit an exam and verify results"
echo "- Check admin sidebar for Semesters/Divisions"
```

---

## 📞 Support

If any test fails:
1. Check server console for errors
2. Check browser console for JavaScript errors
3. Verify database migrations are applied: `python manage.py migrate`
4. Clear browser cache and cookies
5. Try in incognito/private browsing mode

**All systems operational!** 🎉
