import cv2
import mediapipe as mp
import numpy as np
from datetime import datetime, timedelta

class DistractionDetector:
    def __init__(self):
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize state variables
        self.warning_count = 0
        self.warning_limit = 3  # Default warning limit
        self.absence_threshold = 10  # Default absence threshold in seconds
        self.distraction_threshold = 15  # Seconds of continuous distraction before warning (increased from 10)
        
        # Tracking times
        self.last_face_detected_time = None
        self.distraction_start_time = None  # Track when distraction started
        self.last_focused_time = None  # Track when student was last focused
        
        # Freeze management
        self.is_exam_frozen = False
        self.freeze_start_time = None
        self.freeze_duration = 300  # 5 minutes in seconds
        self.last_warning_time = None
        self.warning_cooldown = 10  # 10 seconds between warnings (increased from 5)
        
        # Constants for face detection - MADE LESS SENSITIVE
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        self.GAZE_THRESHOLD = 80  # pixels (increased from 50 - less sensitive)
        self.HEAD_MOVEMENT_THRESHOLD = 150  # pixels (increased from 100 - less sensitive)

    def set_warning_threshold(self, limit):
        """Set the maximum number of warnings before freezing the exam"""
        self.warning_limit = limit

    def set_absence_threshold(self, seconds):
        """Set the time threshold for face absence before issuing a warning"""
        self.absence_threshold = seconds

    def detect_distraction(self, frame):
        """Process a frame and detect distractions"""
        current_time = datetime.now()
        
        # Initialize response with proper time remaining
        response = {
            'face_detected': False,
            'warning_message': '',
            'warning_count': self.warning_count,
            'is_frozen': self.is_exam_frozen,
            'freeze_time_left': 0  # Initialize to 0
        }

        # Calculate freeze time remaining if exam is frozen
        if self.is_exam_frozen and self.freeze_start_time:
            elapsed_time = (current_time - self.freeze_start_time).total_seconds()
            remaining_time = max(0, self.freeze_duration - elapsed_time)
            response['freeze_time_left'] = int(remaining_time)
            
            # Auto-unfreeze if time is up
            if remaining_time <= 0:
                self.unfreeze_exam()
                response['is_frozen'] = False
                response['freeze_time_left'] = 0

        if frame is None:
            response['warning_message'] = 'No video feed available'
            return response

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_height, frame_width = frame.shape[:2]
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2

        # Process the frame
        results = self.face_mesh.process(rgb_frame)

        # Check for face detection
        if not results.multi_face_landmarks:
            if self.last_face_detected_time is None:
                self.last_face_detected_time = current_time
            else:
                time_without_face = (current_time - self.last_face_detected_time).total_seconds()
                if time_without_face >= self.absence_threshold:
                    response['warning_message'] = f'Face not detected for {int(time_without_face)}s'
                    self._handle_warning('Face Missing')
                    self.last_face_detected_time = current_time  # Reset timer after warning
            return response

        # Face is detected
        response['face_detected'] = True
        self.last_face_detected_time = None
        face_landmarks = results.multi_face_landmarks[0]

        # Get mesh coordinates
        mesh_coords = [(int(point.x * frame_width), int(point.y * frame_height))
                      for point in face_landmarks.landmark]

        # Check iris positions
        left_iris = np.array([mesh_coords[idx] for idx in self.LEFT_IRIS])
        right_iris = np.array([mesh_coords[idx] for idx in self.RIGHT_IRIS])
        
        (l_cx, l_cy), _ = cv2.minEnclosingCircle(left_iris)
        (r_cx, r_cy), _ = cv2.minEnclosingCircle(right_iris)

        # Calculate gaze offsets
        left_eye_offset = abs(l_cx - frame_center_x)
        right_eye_offset = abs(r_cx - frame_center_x)
        vertical_offset = abs((l_cy + r_cy) / 2 - frame_center_y)

        # Check head position using nose tip (landmark 1)
        nose = face_landmarks.landmark[1]
        nose_x = int(nose.x * frame_width)
        head_offset = abs(nose_x - frame_center_x)

        # Detect distractions - accumulate time before warning
        is_distracted = False
        distraction_reason = ''
        
        if left_eye_offset > self.GAZE_THRESHOLD or right_eye_offset > self.GAZE_THRESHOLD:
            is_distracted = True
            distraction_reason = 'Looking away from screen'
        elif vertical_offset > self.GAZE_THRESHOLD:
            is_distracted = True
            distraction_reason = 'Looking too high/low'
        elif head_offset > self.HEAD_MOVEMENT_THRESHOLD:
            is_distracted = True
            distraction_reason = 'Head position off-center'
        
        # Handle distraction accumulation
        if is_distracted:
            if self.distraction_start_time is None:
                self.distraction_start_time = current_time
            else:
                distraction_duration = (current_time - self.distraction_start_time).total_seconds()
                if distraction_duration >= self.distraction_threshold:
                    response['warning_message'] = f'{distraction_reason} for {int(distraction_duration)}s'
                    self._handle_warning('Looking Away')
                    self.distraction_start_time = current_time  # Reset timer after warning
                else:
                    # Show message but don't warn yet
                    response['warning_message'] = f'{distraction_reason} ({int(distraction_duration)}s)'
        else:
            # Student is focused - reset distraction timer
            self.distraction_start_time = None
            self.last_focused_time = current_time

        return response

    def _handle_warning(self, violation_type='Distraction'):
        """Handle warning with cooldown period - increments warning count and freezes if limit exceeded"""
        current_time = datetime.now()
        
        # Check if enough time has passed since last warning
        if (self.last_warning_time is None or 
            (current_time - self.last_warning_time).total_seconds() >= self.warning_cooldown):
            
            self.warning_count += 1
            self.last_warning_time = current_time
            self.last_violation_type = violation_type  # Store for logging
            
            # Check if warning limit exceeded - freeze the exam
            if self.warning_count >= self.warning_limit:
                self.freeze_exam()
            
            return True  # Indicate a warning was issued
        return False  # Warning was in cooldown

    def freeze_exam(self):
        """Freeze the exam for the duration specified"""
        if not self.is_exam_frozen:
            self.is_exam_frozen = True
            self.freeze_start_time = datetime.now()
            print(f"EXAM FROZEN at {self.freeze_start_time} for {self.freeze_duration} seconds")

    def unfreeze_exam(self):
        """Unfreeze the exam and reset warnings after freeze duration ends"""
        self.is_exam_frozen = False
        self.freeze_start_time = None
        self.warning_count = 0  # Reset warnings after freeze
        self.last_warning_time = None
        self.distraction_start_time = None  # Reset distraction timer
        print(f"EXAM UNFROZEN - warnings reset")
    
    def faculty_unfreeze_exam(self):
        """Unfreeze exam by faculty intervention - doesn't reset warnings"""
        self.is_exam_frozen = False
        self.freeze_start_time = None
        print(f"EXAM UNFROZEN BY FACULTY")

def main():
    """Run the enhanced distraction detection system."""
    
    # Create detector
    detector = DistractionDetector()
    
    # Start camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return
    
    print("Enhanced Distraction Detection Started")
    print("Press 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process frame
        status = detector.detect_distraction(frame)
        
        # Display status on frame
        frame_height, frame_width = frame.shape[:2]
        status_color = (0, 0, 255) if status['warning_message'] else (0, 255, 0)
        cv2.putText(frame, f"Status: {status['warning_message']}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
        cv2.putText(frame, f"Warnings: {status['warning_count']}/{detector.warning_limit}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        if status['is_frozen']:
            freeze_remaining = int(status['freeze_time_left'])
            cv2.putText(frame, f"EXAM FROZEN - {freeze_remaining}s remaining", 
                      (frame_width//4, frame_height//2),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Show result
        cv2.imshow('Distraction Detection', frame)
        
        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()