import re
import requests
from urllib.parse import urlparse
from .SheetManagerModule import get_questions_from_sheet, extract_sheet_id
import gspread
from google.oauth2.service_account import Credentials
import os
from django.conf import settings

class ExamValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_sheet_url(self, sheet_url):
        """Validate Google Sheets URL format and accessibility"""
        try:
            # Check URL format
            if not sheet_url.startswith('https://docs.google.com/spreadsheets/'):
                self.errors.append("Invalid Google Sheets URL format")
                return False
                
            # Extract sheet ID
            sheet_id = extract_sheet_id(sheet_url)
            if not sheet_id:
                self.errors.append("Could not extract sheet ID from URL")
                return False
                
            # Check if sheet is accessible
            try:
                credentials_path = os.path.join(settings.BASE_DIR, 'core', 'config', 'credentials.json')
                scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
                client = gspread.authorize(creds)
                sheet = client.open_by_key(sheet_id)
                # Try to access the first worksheet
                worksheet = sheet.get_worksheet(0)
                if not worksheet:
                    self.errors.append("No worksheets found in the Google Sheet")
                    return False
                return True
            except Exception as e:
                self.errors.append(f"Cannot access Google Sheet: {str(e)}")
                return False
                
        except Exception as e:
            self.errors.append(f"URL validation error: {str(e)}")
            return False
    
    def validate_question_format(self, questions):
        """Validate question format and required fields"""
        if not questions:
            self.errors.append("No questions found in the sheet")
            return False
            
        required_fields = ['Questions', 'Option A', 'Option B', 'Option C', 'Option D', 'Answer']
        valid_answers = ['A', 'B', 'C', 'D']
        
        for i, question in enumerate(questions, 1):
            # Check required fields
            for field in required_fields:
                if field not in question or not question[field].strip():
                    self.errors.append(f"Question {i}: Missing or empty '{field}' field")
                    return False
            
            # Validate answer format
            answer = question['Answer'].strip().upper()
            if answer not in valid_answers:
                self.errors.append(f"Question {i}: Invalid answer '{answer}'. Must be A, B, C, or D")
                return False
            
            # Check question length
            if len(question['Questions'].strip()) < 10:
                self.warnings.append(f"Question {i}: Question text seems too short")
            
            # Check option lengths
            for option in ['Option A', 'Option B', 'Option C', 'Option D']:
                if len(question[option].strip()) < 2:
                    self.warnings.append(f"Question {i}: {option} seems too short")
        
        return True
    
    def validate_exam_duration(self, duration_minutes):
        """Validate exam duration"""
        try:
            duration = int(duration_minutes)
            if duration < 5:
                self.errors.append("Exam duration must be at least 5 minutes")
                return False
            elif duration > 480:  # 8 hours
                self.errors.append("Exam duration cannot exceed 8 hours")
                return False
            return True
        except ValueError:
            self.errors.append("Invalid exam duration format")
            return False
    
    def validate_exam_date(self, exam_date, exam_time):
        """Validate exam date and time"""
        from datetime import datetime
        from django.utils import timezone
        try:
            date_str = f"{exam_date} {exam_time}"
            exam_datetime_naive = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            # Make timezone-aware using current timezone
            if timezone.is_naive(exam_datetime_naive):
                current_tz = timezone.get_current_timezone()
                exam_datetime = timezone.make_aware(exam_datetime_naive, current_tz)
            else:
                exam_datetime = exam_datetime_naive
            
            # Check if exam is in the future
            if exam_datetime <= timezone.now():
                self.errors.append("Exam date and time must be in the future")
                return False
                
            return True
        except ValueError:
            self.errors.append("Invalid date or time format")
            return False
    
    def validate_exam_title(self, title):
        """Validate exam title"""
        if not title or not title.strip():
            self.errors.append("Exam title is required")
            return False
        
        if len(title.strip()) < 3:
            self.errors.append("Exam title must be at least 3 characters long")
            return False
            
        if len(title.strip()) > 100:
            self.errors.append("Exam title cannot exceed 100 characters")
            return False
            
        return True
    
    def validate_complete_exam(self, title, exam_date, exam_time, duration_minutes, sheet_url):
        """Validate all exam parameters"""
        self.errors = []
        self.warnings = []
        
        # Validate basic fields
        if not self.validate_exam_title(title):
            return False
            
        if not self.validate_exam_date(exam_date, exam_time):
            return False
            
        if not self.validate_exam_duration(duration_minutes):
            return False
            
        if not self.validate_sheet_url(sheet_url):
            return False
        
        # Validate questions
        try:
            questions = get_questions_from_sheet(sheet_url)
            if not self.validate_question_format(questions):
                return False
        except Exception as e:
            self.errors.append(f"Error extracting questions: {str(e)}")
            return False
        
        return True
    
    def get_validation_summary(self):
        """Get validation summary with errors and warnings"""
        return {
            'is_valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }

def validate_exam_data(title, exam_date, exam_time, duration_minutes, sheet_url):
    """Convenience function to validate exam data"""
    validator = ExamValidator()
    is_valid = validator.validate_complete_exam(title, exam_date, exam_time, duration_minutes, sheet_url)
    return validator.get_validation_summary() 