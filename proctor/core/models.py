from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('Student', 'Student'),
        ('Faculty', 'Faculty'),
        ('Admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    email = models.EmailField(unique=True)

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

    def __str__(self):
        return f"{self.title} on {self.date.strftime('%d-%m-%Y %H:%M')}"


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


class Violation(models.Model):
    VIOLATION_TYPES = (
        ('Distraction', 'Distraction'),
        ('Face Missing', 'Face Missing'),
        ('Multiple Faces', 'Multiple Faces'),
    )

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    type = models.CharField(max_length=20, choices=VIOLATION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.type} @ {self.timestamp}"


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
