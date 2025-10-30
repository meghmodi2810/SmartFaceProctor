import threading
import cv2
from datetime import datetime
from django.utils import timezone
from .DistractionDetectionModule import DistractionDetector
from ..models import Violation, Exam
import logging

class ExamMonitor:
    _instances = {}
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, student_id, exam_id):
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
        self.last_error = None
        self.camera_retries = 0
        self.max_retries = 3
        self.last_activity = timezone.now()
        self.warning_count = 0
        self.frozen_at = None
        self.last_violation_type = None
        
    def start_monitoring(self):
        if self.is_running:
            return False
            
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        return True

    def stop_monitoring(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)  # Wait up to 5 seconds
        self._cleanup_camera()
        
        key = f"{self.student_id}_{self.exam_id}"
        with self._lock:
            if key in self._instances:
                del self._instances[key]

    def _cleanup_camera(self):
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                logging.error(f"Error releasing camera: {e}")
            finally:
                self.camera = None

    def _initialize_camera(self):
        if self.camera_retries >= self.max_retries:
            raise RuntimeError("Failed to initialize camera after maximum retries")
            
        self._cleanup_camera()
        self.camera = cv2.VideoCapture(0)
        
        if not self.camera.isOpened():
            self.camera_retries += 1
            raise RuntimeError("Failed to open camera")
        
        # Reset retry count on successful initialization
        self.camera_retries = 0
        return True

    def get_status(self):
        """Get detailed monitoring status"""
        return {
            'is_running': self.is_running,
            'last_error': self.last_error,
            'camera_active': self.camera is not None and self.camera.isOpened(),
            'warning_count': self.warning_count,
            'is_frozen': self.frozen_at is not None,
            'frozen_at': self.frozen_at.isoformat() if self.frozen_at else None,
            'last_activity': self.last_activity.isoformat(),
            'last_violation_type': self.last_violation_type
        }

    def _monitor_loop(self):
        try:
            self._initialize_camera()
            exam = Exam.objects.get(id=self.exam_id)
            
            self.detector.set_warning_threshold(exam.warning_limit)
            self.detector.set_absence_threshold(exam.absence_threshold)
            
            consecutive_failures = 0
            max_consecutive_failures = 5
            
            while self.is_running:
                try:
                    ret, frame = self.camera.read()
                    if not ret:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            self._initialize_camera()
                        continue
                    
                    consecutive_failures = 0  # Reset on successful frame
                    self.last_activity = timezone.now()
                    
                    result = self.detector.detect_distraction(frame)
                    
                    if result['warning_message']:
                        violation_type = 'Face Missing' if 'Face not detected' in result['warning_message'] else 'Distraction'
                        self.last_violation_type = violation_type
                        self.warning_count = result['warning_count']
                        
                        violation = Violation.objects.create(
                            exam_id=self.exam_id,
                            student_id=self.student_id,
                            type=violation_type,
                            message=result['warning_message'],
                            timestamp=timezone.now()
                        )
                        
                        if result['warning_count'] >= exam.warning_limit and not result['is_frozen']:
                            self.detector.freeze_exam()
                            self.frozen_at = timezone.now()
                            # Log the freeze event
                            Violation.objects.create(
                                exam_id=self.exam_id,
                                student_id=self.student_id,
                                type='Exam_Frozen',
                                message=f"Exam frozen after {result['warning_count']} warnings",
                                timestamp=self.frozen_at
                            )

                except Exception as loop_error:
                    logging.error(f"Error in monitoring loop: {loop_error}")
                    self.last_error = str(loop_error)
                    
        except Exception as e:
            self.last_error = str(e)
            logging.error(f"Critical monitoring error: {e}")
        finally:
            self._cleanup_camera()

    def faculty_unfreeze(self):
        """Allow faculty to unfreeze a student's exam"""
        if self.detector:
            self.detector.faculty_unfreeze_exam()
            self.frozen_at = None
            Violation.objects.create(
                exam_id=self.exam_id,
                student_id=self.student_id,
                type='Exam_Unfrozen',
                message="Exam unfrozen by faculty",
                timestamp=timezone.now()
            )