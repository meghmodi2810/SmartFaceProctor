import threading
import cv2
from datetime import datetime
from django.utils import timezone
from .DistractionDetectionModule import DistractionDetector
from ..models import Violation, Exam

class ExamMonitor:
    _instances = {}  # Class variable to store active monitor instances
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, student_id, exam_id):
        """Get or create an ExamMonitor instance for a student's exam"""
        key = f"{student_id}_{exam_id}"
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = cls(student_id, exam_id)
            return cls._instances[key]

    def __init__(self, student_id, exam_id):
        self.student_id = student_id
        self.exam_id = exam_id
        self.detector = DistractionDetector()
        self.is_running = False
        self.thread = None
        self.camera = None
        
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.is_running:
            return False
            
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True  # Thread will be terminated when main program exits
        self.thread.start()
        return True

    def stop_monitoring(self):
        """Stop the monitoring thread gracefully"""
        self.is_running = False
        if self.thread:
            self.thread.join()
        if self.camera:
            self.camera.release()
        
        # Remove instance from class storage
        key = f"{self.student_id}_{self.exam_id}"
        with self._lock:
            if key in self._instances:
                del self._instances[key]

    def _monitor_loop(self):
        """Main monitoring loop that runs in background"""
        try:
            self.camera = cv2.VideoCapture(0)
            exam = Exam.objects.get(id=self.exam_id)
            
            # Configure detector with exam settings
            self.detector.set_warning_threshold(exam.warning_limit)
            self.detector.set_absence_threshold(exam.absence_threshold)
            
            while self.is_running:
                ret, frame = self.camera.read()
                if not ret:
                    continue

                # Process frame and get results
                result = self.detector.detect_distraction(frame)
                
                # Record violation if warning message exists and increment warning count
                if result['warning_message']:
                    violation_type = 'Face Missing' if result['warning_message'] == 'Face not detected' else 'Distraction'
                    Violation.objects.create(
                        exam_id=self.exam_id,
                        student_id=self.student_id,
                        type=violation_type
                    )
                    
                    # Check if we need to freeze the exam
                    if result['warning_count'] >= exam.warning_limit and not result['is_frozen']:
                        self.detector.freeze_exam()

        except Exception as e:
            print(f"Monitoring error: {e}")
        finally:
            if self.camera:
                self.camera.release()