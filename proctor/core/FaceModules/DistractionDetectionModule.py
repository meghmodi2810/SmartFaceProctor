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
        self.last_face_detected_time = None
        self.is_exam_frozen = False
        self.freeze_start_time = None
        self.freeze_duration = 300  # 5 minutes in seconds
        
        # Constants for face detection
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        self.GAZE_THRESHOLD = 50  # pixels
        self.HEAD_MOVEMENT_THRESHOLD = 100  # pixels

    def set_warning_threshold(self, limit):
        """Set the maximum number of warnings before freezing the exam"""
        self.warning_limit = limit

    def set_absence_threshold(self, seconds):
        """Set the time threshold for face absence before issuing a warning"""
        self.absence_threshold = seconds

    def detect_distraction(self, frame):
        """Process a frame and detect distractions"""
        if frame is None:
            return {
                'face_detected': False,
                'warning_message': 'No video feed available',
                'warning_count': self.warning_count,
                'is_frozen': self.is_exam_frozen
            }

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_height, frame_width = frame.shape[:2]
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2

        # Process the frame
        results = self.face_mesh.process(rgb_frame)
        
        # Initialize response
        response = {
            'face_detected': False,
            'warning_message': '',
            'warning_count': self.warning_count,
            'is_frozen': self.is_exam_frozen,
            'freeze_time_left': None
        }

        # Update freeze status if active
        if self.is_exam_frozen:
            if self.freeze_start_time:
                elapsed_time = (datetime.now() - self.freeze_start_time).total_seconds()
                if elapsed_time >= self.freeze_duration:
                    self.unfreeze_exam()
                else:
                    response['freeze_time_left'] = self.freeze_duration - elapsed_time

        # Check for face detection
        if not results.multi_face_landmarks:
            # Update last face detection time
            if self.last_face_detected_time is None:
                self.last_face_detected_time = datetime.now()
            else:
                time_without_face = (datetime.now() - self.last_face_detected_time).total_seconds()
                if time_without_face >= self.absence_threshold:
                    response['warning_message'] = 'Face not detected'
                    self.issue_warning()
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

        # Detect distractions
        if left_eye_offset > self.GAZE_THRESHOLD or right_eye_offset > self.GAZE_THRESHOLD:
            response['warning_message'] = 'Looking away from screen'
            self.issue_warning()
        elif vertical_offset > self.GAZE_THRESHOLD:
            response['warning_message'] = 'Looking too high/low'
            self.issue_warning()
        elif head_offset > self.HEAD_MOVEMENT_THRESHOLD:
            response['warning_message'] = 'Head position too far from center'
            self.issue_warning()

        return response

    def issue_warning(self):
        """Issue a warning and check if exam should be frozen"""
        if not self.is_exam_frozen:
            self.warning_count += 1
            if self.warning_count >= self.warning_limit:
                self.freeze_exam()

    def freeze_exam(self):
        """Freeze the exam"""
        self.is_exam_frozen = True
        self.freeze_start_time = datetime.now()

    def unfreeze_exam(self):
        """Unfreeze the exam and reset warnings"""
        self.is_exam_frozen = False
        self.freeze_start_time = None
        self.warning_count = 0

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