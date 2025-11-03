from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Submission, Exam
from django.db.models import Avg, Max, Count

@login_required
def student_results(request):
    """Display student's exam results with grades and statistics"""
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    # Get all submissions for this student
    submissions = Submission.objects.filter(student=user).select_related('exam').order_by('-submitted_on')
    
    # Calculate grade for each submission and format score to 2 decimals
    for submission in submissions:
        submission.grade = calculate_grade(submission.score)
        submission.score = round(submission.score, 2)  # Format to 2 decimal places
    
    # Calculate statistics
    if submissions.exists():
        scores = [s.score for s in submissions]
        total_exams = submissions.count()
        average_score = round(sum(scores) / len(scores), 2)  # 2 decimal places
        highest_score = round(max(scores), 2)  # 2 decimal places
        
        # Calculate average grade
        grades = [calculate_grade(s.score) for s in submissions]
        grade_points = {'O': 5.0, 'A': 4.0, 'B': 3.0, 'C': 2.0, 'F': 0.0}
        avg_grade_point = sum(grade_points.get(g, 0) for g in grades) / len(grades)
        
        if avg_grade_point >= 4.5:
            average_grade = 'O'
        elif avg_grade_point >= 3.0:
            average_grade = 'A'
        elif avg_grade_point >= 2.0:
            average_grade = 'B'
        elif avg_grade_point >= 1.0:
            average_grade = 'C'
        else:
            average_grade = 'F'
    else:
        total_exams = 0
        average_score = 0.00
        highest_score = 0.00
        average_grade = 'N/A'
    
    context = {
        'student': user,
        'submissions': submissions,
        'total_exams': total_exams,
        'average_score': average_score,
        'highest_score': highest_score,
        'average_grade': average_grade,
    }
    
    return render(request, 'student_results.html', context)


def calculate_grade(score):
    """Calculate letter grade from percentage score"""
    if score >= 90:
        return 'O'  # Outstanding
    elif score >= 70:
        return 'A'  # Excellent
    elif score >= 50:
        return 'B'  # Good
    elif score >= 34:
        return 'C'  # Average
    else:
        return 'F'  # Fail
