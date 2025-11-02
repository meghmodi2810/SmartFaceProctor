from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Department(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Semester(models.Model):
    name = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='semesters')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['department', 'name']
        unique_together = ('name', 'department')

    def __str__(self):
        return f"{self.name} - {self.department.name}"


class Division(models.Model):
    name = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='divisions')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='divisions', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['department', 'semester', 'name']
        unique_together = ('name', 'department', 'semester')

    def __str__(self):
        sem = f"{self.semester.name} - " if self.semester else ""
        return f"{sem}{self.name} - {self.department.name}"

class User(AbstractUser):
    ROLE_CHOICES = (
        ('Student', 'Student'),
        ('Faculty', 'Faculty'),
        ('Admin', 'Admin'),
    )
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    email = models.EmailField(unique=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    branch = models.CharField(max_length=100, null=True, blank=True)
    course = models.CharField(max_length=100, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True)
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True, blank=True)
    current_semester = models.IntegerField(null=True, blank=True)
    specialization = models.CharField(max_length=100, null=True, blank=True)
    qualification = models.CharField(max_length=100, null=True, blank=True)
    is_profile_complete = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return f"{self.username} ({self.role})"


class Exam(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Faculty'})
    sheet_url = models.URLField(blank=True, null=True)
    is_selective = models.BooleanField(default=False, help_text="If True, only assigned students can take this exam")
    warning_limit = models.IntegerField(default=3)
    absence_threshold = models.IntegerField(default=10)  # seconds before counting as absent

    def __str__(self):
        return f"{self.title} on {self.date.strftime('%d-%m-%Y %H:%M')}"

    @property
    def is_ongoing(self):
        now = timezone.now()
        end_time = self.date + timezone.timedelta(minutes=self.duration_minutes)
        return self.date <= now <= end_time


class ExamAssignment(models.Model):
    """Model to handle selective student assignments to exams"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_assignments_made', limit_choices_to={'role__in': ['Faculty', 'Admin']})
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('exam', 'student')
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.student.username} assigned to {self.exam.title}"


class Submission(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    score = models.FloatField()
    submitted_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"


class ExamProgress(models.Model):
    """Store partial exam answers for auto-save functionality"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    answers = models.JSONField(default=dict)  # {question_id: answer}
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['exam', 'student']


class ExamFeedback(models.Model):
    """Store student feedback after completing exam"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='feedbacks')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    rating = models.IntegerField(choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)])  # 1-5 stars
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['exam', 'student']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} ({self.rating} stars)"


class Violation(models.Model):
    VIOLATION_TYPES = (
        ('Distraction', 'Distraction'),
        ('Face Missing', 'Face Missing'),
        ('Multiple Faces', 'Multiple Faces'),
        ('Warning Limit Exceeded', 'Warning Limit Exceeded'),
        ('Looking Away', 'Looking Away'),
    )

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='violations')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    type = models.CharField(max_length=50, choices=VIOLATION_TYPES)  # Increased from 20 to 50
    details = models.TextField(blank=True, null=True)  # Additional details about the violation
    message = models.CharField(max_length=255, blank=True, null=True)  # Warning message shown to student
    timestamp = models.DateTimeField(auto_now_add=True)
    is_frozen = models.BooleanField(default=False)  # Track if this violation caused freeze
    freeze_cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_freezes', limit_choices_to={'role': 'Faculty'})

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.student.username} - {self.type} @ {self.timestamp}"


class ExamAttempt(models.Model):
    """Track exam attempts to prevent multiple attempts"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    can_reattempt = models.BooleanField(default=False)  # Faculty can enable this
    reset_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='exam_resets', limit_choices_to={'role': 'Faculty'})
    reset_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('exam', 'student')
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} - Attempted at {self.started_at}"


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    answer = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.text[:50]}..."


class BugReport(models.Model):
    BUG_TYPE_CHOICES = (
        ('technical', 'Technical Issue'),
        ('ui_ux', 'UI/UX Problem'),
        ('performance', 'Performance Issue'),
        ('security', 'Security Concern'),
        ('other', 'Other'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )
    
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    bug_type = models.CharField(max_length=20, choices=BUG_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    browser = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.reporter.username}"


class PasswordResetOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.email} - {self.otp}"
    
    def is_expired(self):
        """Check if OTP is expired (15 minutes)"""
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(minutes=15)


class NotificationRead(models.Model):
    """Track which exam notifications students have marked as read"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    marked_read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student', 'exam')
        ordering = ['-marked_read_at']
    
    def __str__(self):
        return f"{self.student.username} marked {self.exam.title} as read"
