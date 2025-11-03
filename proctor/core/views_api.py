from django.http import JsonResponse
import traceback
import sys

def get_semesters(request, department_id):
    """API endpoint to fetch semesters for a department"""
    # Manual authentication check for API
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        # Import models inside function to catch import errors
        try:
            from .models import Department, Semester
        except ImportError as ie:
            return JsonResponse({
                'success': False,
                'error': f'Import Error: {str(ie)}',
                'traceback': traceback.format_exc()
            })
        
        try:
            department = Department.objects.get(id=department_id, is_active=True)
        except Department.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Department with id {department_id} not found'
            })
        
        semesters = Semester.objects.filter(department=department, is_active=True).order_by('name')
        
        semester_list = [
            {'id': sem.id, 'name': sem.name}
            for sem in semesters
        ]
        
        return JsonResponse({
            'success': True,
            'semesters': semester_list,
            'count': len(semester_list)
        })
    except Exception as e:
        # Catch all exceptions and return JSON
        return JsonResponse({
            'success': False,
            'error': f'{type(e).__name__}: {str(e)}',
            'traceback': traceback.format_exc(),
            'exception_type': str(type(e))
        })

def get_divisions(request, department_id, semester_id):
    """API endpoint to fetch divisions for a department and semester"""
    # Manual authentication check for API
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        # Import models inside function to catch import errors
        try:
            from .models import Department, Semester, Division
        except ImportError as ie:
            return JsonResponse({
                'success': False,
                'error': f'Import Error: {str(ie)}',
                'traceback': traceback.format_exc()
            })
        
        try:
            department = Department.objects.get(id=department_id, is_active=True)
        except Department.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Department with id {department_id} not found'
            })
        
        try:
            semester = Semester.objects.get(id=semester_id, department=department, is_active=True)
        except Semester.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Semester with id {semester_id} not found for department {department_id}'
            })
        
        divisions = Division.objects.filter(
            department=department, 
            semester=semester, 
            is_active=True
        ).order_by('name')
        
        division_list = [
            {'id': div.id, 'name': div.name}
            for div in divisions
        ]
        
        return JsonResponse({
            'success': True,
            'divisions': division_list,
            'count': len(division_list)
        })
    except Exception as e:
        # Catch all exceptions and return JSON
        return JsonResponse({
            'success': False,
            'error': f'{type(e).__name__}: {str(e)}',
            'traceback': traceback.format_exc(),
            'exception_type': str(type(e))
        })
