from django.utils import timezone
from .models import Exam, ExamAssignment

def student_notifications(request):
    """Add upcoming exams count to context for all student pages"""
    context = {}
    
    if request.user.is_authenticated and request.user.role == 'Student':
        # Get upcoming exams for this student
        current_time = timezone.now()
        
        # Get all exams that haven't ended yet
        future_exams = Exam.objects.filter(
            date__gte=current_time
        ).select_related('created_by')
        
        # Filter based on selective assignment
        if future_exams.exists():
            from .models import ExamAssignment
            # Get IDs of exams where student is assigned
            selective_exam_ids = set(ExamAssignment.objects.filter(
                student=request.user,
                exam_id__in=[e.id for e in future_exams],
                is_active=True
            ).values_list('exam_id', flat=True))
            
            # Count exams that are either non-selective OR student is assigned
            upcoming_count = sum(1 for exam in future_exams 
                               if not exam.is_selective or exam.id in selective_exam_ids)
            context['upcoming_exams_count'] = upcoming_count
        else:
            context['upcoming_exams_count'] = 0
    else:
        context['upcoming_exams_count'] = 0
    
    return context
