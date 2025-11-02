# Smart Face Proctor System - Database Design & Data Dictionary

## System Overview
The Smart Face Proctor System is an AI-powered online examination proctoring platform that uses facial recognition and distraction detection to monitor students during exams. The system supports multiple user roles (Admin, Faculty, Student) and provides comprehensive exam management, real-time monitoring, violation tracking, and automated grading features.

---

## Database Schema

### Core Tables

✓ **tblUser** ( id [pk], username, password, first_name, last_name, email, role, dob, gender, mobile_number, address, branch, course, department_id [fk], semester_id [fk], division_id [fk], current_semester, specialization, qualification, is_profile_complete, is_active, is_staff, is_superuser, date_joined, last_login )

✓ **tblDepartment** ( id [pk], name, is_active, created_at )

✓ **tblSemester** ( id [pk], name, department_id [fk], is_active, created_at )

✓ **tblDivision** ( id [pk], name, department_id [fk], semester_id [fk], is_active, created_at )

### Exam Management Tables

✓ **tblExam** ( id [pk], title, description, date, duration_minutes, created_by_id [fk], sheet_url, is_selective, warning_limit, absence_threshold )

✓ **tblExamAssignment** ( id [pk], exam_id [fk], student_id [fk], assigned_by_id [fk], assigned_at, is_active )

✓ **tblQuestion** ( id [pk], exam_id [fk], text, option_a, option_b, option_c, option_d, answer )

✓ **tblSubmission** ( id [pk], exam_id [fk], student_id [fk], score, submitted_on )

✓ **tblExamProgress** ( id [pk], exam_id [fk], student_id [fk], answers, last_updated, created_at )

✓ **tblExamAttempt** ( id [pk], exam_id [fk], student_id [fk], started_at, ended_at, is_active, can_reattempt, reset_by_id [fk], reset_at )

### Monitoring & Feedback Tables

✓ **tblViolation** ( id [pk], exam_id [fk], student_id [fk], type, details, message, timestamp, is_frozen, freeze_cancelled_by_id [fk] )

✓ **tblExamFeedback** ( id [pk], exam_id [fk], student_id [fk], rating, description, created_at )

✓ **tblBugReport** ( id [pk], reporter_id [fk], bug_type, priority, title, description, browser, status, created_at, updated_at )

### Security & Authentication Tables

✓ **tblPasswordResetOTP** ( id [pk], email, otp, created_at, is_used )

---

## Complete Data Dictionary

---

### Table: tblUser
**Purpose:** Stores information for all system users (Students, Faculty, Admin) with role-based attributes

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique identifier for user |
| username | VARCHAR | 150 | No | - | Unique | Login username (unique) |
| password | VARCHAR | 128 | No | - | - | Hashed password using PBKDF2 |
| first_name | VARCHAR | 150 | Yes | NULL | - | User's first name |
| last_name | VARCHAR | 150 | Yes | NULL | - | User's last name |
| email | VARCHAR | 254 | No | - | Unique | User's email address (unique) |
| role | VARCHAR | 10 | No | - | - | User role: 'Student', 'Faculty', or 'Admin' |
| dob | DATE | - | Yes | NULL | - | Date of birth |
| gender | VARCHAR | 1 | Yes | NULL | - | Gender: 'M' (Male), 'F' (Female), 'O' (Other) |
| mobile_number | VARCHAR | 15 | Yes | NULL | - | Contact phone number |
| address | TEXT | - | Yes | NULL | - | Residential address |
| branch | VARCHAR | 100 | Yes | NULL | - | Academic branch/stream |
| course | VARCHAR | 100 | Yes | NULL | - | Course name |
| department_id | BigInteger | - | Yes | NULL | FK | Reference to tblDepartment |
| semester_id | BigInteger | - | Yes | NULL | FK | Reference to tblSemester |
| division_id | BigInteger | - | Yes | NULL | FK | Reference to tblDivision |
| current_semester | INTEGER | - | Yes | NULL | - | Current semester number |
| specialization | VARCHAR | 100 | Yes | NULL | - | Area of specialization (Faculty) |
| qualification | VARCHAR | 100 | Yes | NULL | - | Highest qualification (Faculty) |
| is_profile_complete | BOOLEAN | - | No | False | - | Whether profile setup is complete |
| is_active | BOOLEAN | - | No | True | - | Account active status |
| is_staff | BOOLEAN | - | No | False | - | Django admin access |
| is_superuser | BOOLEAN | - | No | False | - | Django superuser status |
| date_joined | DATETIME | - | No | Now() | - | Account creation timestamp |
| last_login | DATETIME | - | Yes | NULL | - | Last login timestamp |

**Relationships:**
- One-to-Many with tblExam (as created_by)
- One-to-Many with tblSubmission (as student)
- One-to-Many with tblViolation (as student)
- One-to-Many with tblExamAssignment (as student and assigned_by)
- Many-to-One with tblDepartment
- Many-to-One with tblSemester
- Many-to-One with tblDivision

**Constraints:**
- Unique: username, email
- Check: role IN ('Student', 'Faculty', 'Admin')
- Check: gender IN ('M', 'F', 'O')

---

### Table: tblDepartment
**Purpose:** Stores academic department information

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique department identifier |
| name | VARCHAR | 100 | No | - | - | Department name (e.g., Computer Science) |
| is_active | BOOLEAN | - | No | True | - | Whether department is currently active |
| created_at | DATETIME | - | No | Now() | - | Record creation timestamp |

**Relationships:**
- One-to-Many with tblSemester
- One-to-Many with tblDivision
- One-to-Many with tblUser

**Constraints:**
- None

---

### Table: tblSemester
**Purpose:** Stores semester/term information for each department

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique semester identifier |
| name | VARCHAR | 50 | No | - | - | Semester name (e.g., "Semester 1", "Fall 2024") |
| department_id | BigInteger | - | No | - | FK | Reference to tblDepartment |
| is_active | BOOLEAN | - | No | True | - | Whether semester is currently active |
| created_at | DATETIME | - | No | Now() | - | Record creation timestamp |

**Relationships:**
- Many-to-One with tblDepartment
- One-to-Many with tblDivision
- One-to-Many with tblUser

**Constraints:**
- Unique Together: (name, department_id)

---

### Table: tblDivision
**Purpose:** Stores class division/section information

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique division identifier |
| name | VARCHAR | 50 | No | - | - | Division name (e.g., "Division A", "Section B") |
| department_id | BigInteger | - | No | - | FK | Reference to tblDepartment |
| semester_id | BigInteger | - | Yes | NULL | FK | Reference to tblSemester |
| is_active | BOOLEAN | - | No | True | - | Whether division is currently active |
| created_at | DATETIME | - | No | Now() | - | Record creation timestamp |

**Relationships:**
- Many-to-One with tblDepartment
- Many-to-One with tblSemester
- One-to-Many with tblUser

**Constraints:**
- Unique Together: (name, department_id, semester_id)

---

### Table: tblExam
**Purpose:** Stores exam information created by faculty

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique exam identifier |
| title | VARCHAR | 100 | No | - | - | Exam title/name |
| description | TEXT | - | Yes | NULL | - | Detailed exam description |
| date | DATETIME | - | No | - | - | Exam scheduled date and time |
| duration_minutes | INTEGER | Positive | No | - | - | Exam duration in minutes |
| created_by_id | BigInteger | - | No | - | FK | Reference to tblUser (Faculty) |
| sheet_url | VARCHAR | 200 | Yes | NULL | - | URL to question paper/Google Sheet |
| is_selective | BOOLEAN | - | No | False | - | If True, only assigned students can take exam |
| warning_limit | INTEGER | - | No | 3 | - | Maximum warnings before exam freeze |
| absence_threshold | INTEGER | - | No | 10 | - | Seconds before face absence triggers warning |

**Relationships:**
- Many-to-One with tblUser (created_by)
- One-to-Many with tblExamAssignment
- One-to-Many with tblQuestion
- One-to-Many with tblSubmission
- One-to-Many with tblViolation
- One-to-Many with tblExamAttempt
- One-to-Many with tblExamProgress
- One-to-Many with tblExamFeedback

**Constraints:**
- Check: duration_minutes > 0

---

### Table: tblExamAssignment
**Purpose:** Manages selective exam assignments to specific students

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique assignment identifier |
| exam_id | BigInteger | - | No | - | FK | Reference to tblExam |
| student_id | BigInteger | - | No | - | FK | Reference to tblUser (Student) |
| assigned_by_id | BigInteger | - | No | - | FK | Reference to tblUser (Faculty/Admin) |
| assigned_at | DATETIME | - | No | Now() | - | Assignment creation timestamp |
| is_active | BOOLEAN | - | No | True | - | Whether assignment is active |

**Relationships:**
- Many-to-One with tblExam
- Many-to-One with tblUser (student)
- Many-to-One with tblUser (assigned_by)

**Constraints:**
- Unique Together: (exam_id, student_id)

---

### Table: tblQuestion
**Purpose:** Stores MCQ questions for each exam

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique question identifier |
| exam_id | BigInteger | - | No | - | FK | Reference to tblExam |
| text | TEXT | - | No | - | - | Question text |
| option_a | VARCHAR | 255 | No | - | - | Option A text |
| option_b | VARCHAR | 255 | No | - | - | Option B text |
| option_c | VARCHAR | 255 | No | - | - | Option C text |
| option_d | VARCHAR | 255 | No | - | - | Option D text |
| answer | VARCHAR | 10 | No | - | - | Correct answer: 'A', 'B', 'C', or 'D' |

**Relationships:**
- Many-to-One with tblExam

**Constraints:**
- None

---

### Table: tblSubmission
**Purpose:** Stores exam submission results and scores

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique submission identifier |
| exam_id | BigInteger | - | No | - | FK | Reference to tblExam |
| student_id | BigInteger | - | No | - | FK | Reference to tblUser (Student) |
| score | FLOAT | - | No | - | - | Percentage score (0-100) |
| submitted_on | DATETIME | - | No | Now() | - | Submission timestamp |

**Relationships:**
- Many-to-One with tblExam
- Many-to-One with tblUser (student)

**Constraints:**
- Check: score >= 0 AND score <= 100

---

### Table: tblExamProgress
**Purpose:** Auto-saves student answers during exam for recovery

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique progress identifier |
| exam_id | BigInteger | - | No | - | FK | Reference to tblExam |
| student_id | BigInteger | - | No | - | FK | Reference to tblUser (Student) |
| answers | JSON | - | No | {} | - | JSON object storing {question_id: answer} |
| last_updated | DATETIME | - | No | Now() | - | Last auto-save timestamp |
| created_at | DATETIME | - | No | Now() | - | First save timestamp |

**Relationships:**
- Many-to-One with tblExam
- Many-to-One with tblUser (student)

**Constraints:**
- Unique Together: (exam_id, student_id)

---

### Table: tblExamAttempt
**Purpose:** Tracks exam attempts to prevent multiple submissions

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique attempt identifier |
| exam_id | BigInteger | - | No | - | FK | Reference to tblExam |
| student_id | BigInteger | - | No | - | FK | Reference to tblUser (Student) |
| started_at | DATETIME | - | No | Now() | - | Exam start timestamp |
| ended_at | DATETIME | - | Yes | NULL | - | Exam end timestamp |
| is_active | BOOLEAN | - | No | True | - | Whether attempt is currently active |
| can_reattempt | BOOLEAN | - | No | False | - | Faculty-granted reattempt permission |
| reset_by_id | BigInteger | - | Yes | NULL | FK | Reference to tblUser (Faculty) who allowed reset |
| reset_at | DATETIME | - | Yes | NULL | - | Reset permission timestamp |

**Relationships:**
- Many-to-One with tblExam
- Many-to-One with tblUser (student)
- Many-to-One with tblUser (reset_by)

**Constraints:**
- Unique Together: (exam_id, student_id)

---

### Table: tblViolation
**Purpose:** Logs proctoring violations detected during exams

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique violation identifier |
| exam_id | BigInteger | - | No | - | FK | Reference to tblExam |
| student_id | BigInteger | - | No | - | FK | Reference to tblUser (Student) |
| type | VARCHAR | 50 | No | - | - | Violation type: 'Distraction', 'Face Missing', 'Multiple Faces', 'Looking Away', 'Warning Limit Exceeded' |
| details | TEXT | - | Yes | NULL | - | Additional violation details |
| message | VARCHAR | 255 | Yes | NULL | - | Warning message shown to student |
| timestamp | DATETIME | - | No | Now() | - | Violation occurrence timestamp |
| is_frozen | BOOLEAN | - | No | False | - | Whether this violation caused exam freeze |
| freeze_cancelled_by_id | BigInteger | - | Yes | NULL | FK | Reference to tblUser (Faculty) who cancelled freeze |

**Relationships:**
- Many-to-One with tblExam
- Many-to-One with tblUser (student)
- Many-to-One with tblUser (freeze_cancelled_by)

**Constraints:**
- Check: type IN ('Distraction', 'Face Missing', 'Multiple Faces', 'Looking Away', 'Warning Limit Exceeded')

---

### Table: tblExamFeedback
**Purpose:** Stores student feedback after completing exams

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique feedback identifier |
| exam_id | BigInteger | - | No | - | FK | Reference to tblExam |
| student_id | BigInteger | - | No | - | FK | Reference to tblUser (Student) |
| rating | INTEGER | 1-5 | No | - | - | Star rating (1-5 stars) |
| description | TEXT | - | Yes | NULL | - | Detailed feedback text |
| created_at | DATETIME | - | No | Now() | - | Feedback submission timestamp |

**Relationships:**
- Many-to-One with tblExam
- Many-to-One with tblUser (student)

**Constraints:**
- Unique Together: (exam_id, student_id)
- Check: rating >= 1 AND rating <= 5

---

### Table: tblBugReport
**Purpose:** Stores bug reports submitted by students

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique bug report identifier |
| reporter_id | BigInteger | - | No | - | FK | Reference to tblUser (Student) |
| bug_type | VARCHAR | 20 | No | - | - | Bug category: 'technical', 'ui_ux', 'performance', 'security', 'other' |
| priority | VARCHAR | 10 | No | - | - | Priority level: 'low', 'medium', 'high' |
| title | VARCHAR | 200 | No | - | - | Brief bug title |
| description | TEXT | - | No | - | - | Detailed bug description |
| browser | VARCHAR | 100 | Yes | NULL | - | Browser information |
| status | VARCHAR | 15 | No | 'open' | - | Status: 'open', 'in_progress', 'resolved', 'closed' |
| created_at | DATETIME | - | No | Now() | - | Report creation timestamp |
| updated_at | DATETIME | - | No | Now() | - | Last update timestamp |

**Relationships:**
- Many-to-One with tblUser (reporter)

**Constraints:**
- Check: bug_type IN ('technical', 'ui_ux', 'performance', 'security', 'other')
- Check: priority IN ('low', 'medium', 'high')
- Check: status IN ('open', 'in_progress', 'resolved', 'closed')

---

### Table: tblPasswordResetOTP
**Purpose:** Stores OTP codes for password reset functionality

| Field Name | Data Type | Size/Constraint | Null | Default | Key | Description |
|------------|-----------|-----------------|------|---------|-----|-------------|
| id | BigInteger | Auto | No | Auto | PK | Unique OTP record identifier |
| email | VARCHAR | 254 | No | - | - | Email address for password reset |
| otp | VARCHAR | 6 | No | - | - | 6-digit OTP code |
| created_at | DATETIME | - | No | Now() | - | OTP generation timestamp |
| is_used | BOOLEAN | - | No | False | - | Whether OTP has been used |

**Relationships:**
- None (uses email, not foreign key to User table)

**Constraints:**
- None

**Business Rules:**
- OTP expires after 15 minutes
- OTP can only be used once

---

## Entity Relationship Diagram (ERD) Summary

### Primary Entities:
1. **User** - Central entity for all system users
2. **Department, Semester, Division** - Academic structure hierarchy
3. **Exam** - Core exam entity
4. **Question** - MCQ questions for exams
5. **Submission** - Exam results
6. **Violation** - Proctoring violations

### Key Relationships:
- User (Faculty) → creates → Exam (1:N)
- Exam → contains → Question (1:N)
- User (Student) → takes → Exam → produces → Submission (1:1)
- User (Student) → during → Exam → may have → Violation (1:N)
- Exam (Selective) → assigned to → User (Student) via ExamAssignment (M:N)
- Department → has → Semester → has → Division (1:N:N)

---

## Database Statistics

**Total Tables:** 14
**Total Relationships:** 25+
**User Roles:** 3 (Student, Faculty, Admin)
**Exam Types:** 2 (General, Selective)
**Violation Types:** 5
**Bug Report Types:** 5

---

## Security Features

1. **Password Hashing:** PBKDF2 algorithm with SHA256
2. **OTP Expiration:** 15-minute validity
3. **One-Time Use:** OTP can only be used once
4. **Role-Based Access:** Enforced at model level
5. **Cascade Deletion Protection:** SET_NULL on critical foreign keys

---

## Performance Optimizations

1. **Indexes:** Primary keys, foreign keys, unique constraints
2. **Ordering:** Default ordering on timestamp fields
3. **Select Related:** Optimized queries using select_related()
4. **JSON Storage:** Efficient storage for variable exam answers
5. **Unique Together:** Prevents duplicate records

---

## Backup & Recovery

- **Auto-save:** ExamProgress table stores partial answers every few seconds
- **Audit Trail:** Timestamps on all major operations
- **Soft Deletes:** is_active flags instead of hard deletes
- **Violation Logging:** Complete history of all proctoring events

---

## System Constraints & Business Rules

1. Email addresses must be unique across all users
2. Students can only submit an exam once (unless reset by faculty)
3. OTP expires after 15 minutes
4. Exam warnings accumulate; exceeding limit freezes the exam
5. Selective exams require explicit assignment to students
6. Faculty can cancel exam freezes and allow reattempts
7. Violations are logged even if student passes the exam
8. Exam feedback can only be submitted once per student per exam

---

*This database design supports a comprehensive online proctoring system with real-time monitoring, automated grading, and detailed analytics.*
