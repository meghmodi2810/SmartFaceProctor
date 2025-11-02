import cv2
import mediapipe as mp
import numpy as np
from datetime import datetime, timedelta

class DistractionDetector:
    def __init__(self):
        # Initialize MediaPipe Face Mesh with optimized settings
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=2,  # Detect up to 2 faces for multiple person detection
            refine_landmarks=True,
            min_detection_confidence=0.6,  # Increased for better accuracy
            min_tracking_confidence=0.6
        )
        
        # Initialize state variables
        self.warning_count = 0
        self.warning_limit = 3  # Default warning limit
        self.absence_threshold = 8  # More lenient: 8 seconds
        self.distraction_threshold = 10  # More lenient: 10 seconds
        
        # Tracking times
        self.last_face_detected_time = None
        self.distraction_start_time = None
        self.last_focused_time = None
        self.calibration_frames = 0
        self.calibration_complete = False
        self.system_ready = False  # NEW: Track if system is fully initialized
        self.initialization_start_time = None  # NEW: Track initialization start
        
        # Movement tracking - NEW
        self.prev_nose_pos = None
        self.prev_iris_pos = None
        self.movement_history = []  # Track last 5 frames of movement
        self.MOVEMENT_HISTORY_SIZE = 5
        
        # Freeze management
        self.is_exam_frozen = False
        self.freeze_start_time = None
        self.freeze_duration = 300  # 5 minutes
        self.last_warning_time = None
        self.warning_cooldown = 10  # More lenient: 10 seconds between warnings
        
        # Face landmarks for detection
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        self.NOSE_TIP = 1
        self.CHIN = 152
        
        # LENIENT thresholds - Less sensitive for better user experience
        self.GAZE_THRESHOLD = 60  # More lenient: 60 pixels (was 30)
        self.HEAD_MOVEMENT_THRESHOLD = 100  # More lenient: 100 pixels (was 60)
        self.VERTICAL_GAZE_THRESHOLD = 50  # More lenient: 50 pixels (was 25)
        self.MOVEMENT_THRESHOLD = 40  # More lenient: 40 pixels (was 20)
        self.EXCESSIVE_MOVEMENT_THRESHOLD = 70  # More lenient: 70 pixels (was 35)
        
        # Calibration data
        self.baseline_nose_x = None
        self.baseline_iris_x = None
        
        # Multiple face detection - More lenient
        self.multiple_face_start_time = None
        self.multiple_face_threshold = 5  # More lenient: 5 seconds

    def set_warning_threshold(self, limit):
        """Set the maximum number of warnings before freezing the exam"""
        self.warning_limit = limit

    def set_absence_threshold(self, seconds):
        """Set the time threshold for face absence before issuing a warning"""
        self.absence_threshold = seconds

    def set_distraction_threshold(self, seconds):
        """Set the time threshold for distraction before issuing a warning"""
        self.distraction_threshold = seconds

    def detect_distraction(self, frame):
        """Process a frame and detect distractions with improved accuracy"""
        current_time = datetime.now()
        
        # Initialize response
        response = {
            'face_detected': False,
            'warning_message': '',
            'warning_count': self.warning_count,
            'is_frozen': self.is_exam_frozen,
            'freeze_time_left': 0,
            'multiple_faces': False
        }

        # Handle frozen exam
        if self.is_exam_frozen and self.freeze_start_time:
            elapsed_time = (current_time - self.freeze_start_time).total_seconds()
            remaining_time = max(0, self.freeze_duration - elapsed_time)
            response['freeze_time_left'] = int(remaining_time)
            
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

        # Check for multiple faces
        if results.multi_face_landmarks and len(results.multi_face_landmarks) > 1:
            response['multiple_faces'] = True
            if self.multiple_face_start_time is None:
                self.multiple_face_start_time = current_time
            else:
                duration = (current_time - self.multiple_face_start_time).total_seconds()
                if duration >= self.multiple_face_threshold:
                    response['warning_message'] = f'Multiple faces detected for {int(duration)}s'
                    self._handle_warning('Multiple Faces')
                    self.multiple_face_start_time = current_time
                else:
                    response['warning_message'] = f'Multiple faces detected ({int(duration)}s)'
            return response
        else:
            self.multiple_face_start_time = None

        # Check for face absence - DELAYED FEEDBACK (more lenient)
        if not results.multi_face_landmarks:
            # During initialization/calibration, be very lenient
            if not self.system_ready:
                response['warning_message'] = '🔄 Initializing camera... Please look at the screen'
                return response
            
            if self.last_face_detected_time is None:
                self.last_face_detected_time = current_time
                # Show gentle reminder instead of immediate warning
                response['warning_message'] = '📸 Adjusting camera...'
            else:
                time_without_face = (current_time - self.last_face_detected_time).total_seconds()
                
                # Only show warning after a few seconds (more lenient)
                if time_without_face >= 4:
                    response['warning_message'] = f'⚠️ Please ensure your face is visible ({int(time_without_face)}s)'
                else:
                    response['warning_message'] = '📸 Adjusting camera...'
                
                # Issue warning after threshold (now 8 seconds)
                if time_without_face >= self.absence_threshold:
                    self._handle_warning('Face Missing')
                    # Don't reset timer - keep accumulating to show continuous absence
            return response

        # Single face detected
        response['face_detected'] = True
        self.last_face_detected_time = None
        face_landmarks = results.multi_face_landmarks[0]

        # Get mesh coordinates
        mesh_coords = [(int(point.x * frame_width), int(point.y * frame_height))
                      for point in face_landmarks.landmark]

        # Calibration phase (extended for better accuracy and user experience)
        if self.calibration_frames < 60:  # Extended to 60 frames (~2 seconds)
            if self.initialization_start_time is None:
                self.initialization_start_time = current_time
            
            nose_x = mesh_coords[self.NOSE_TIP][0]
            left_iris = np.array([mesh_coords[idx] for idx in self.LEFT_IRIS])
            (l_cx, _), _ = cv2.minEnclosingCircle(left_iris)
            
            if self.baseline_nose_x is None:
                self.baseline_nose_x = nose_x
                self.baseline_iris_x = l_cx
            else:
                # Average with existing baseline
                self.baseline_nose_x = (self.baseline_nose_x + nose_x) / 2
                self.baseline_iris_x = (self.baseline_iris_x + l_cx) / 2
            
            self.calibration_frames += 1
            
            # Show user-friendly calibration message
            progress = int((self.calibration_frames / 60) * 100)
            response['warning_message'] = f'🔄 Calibrating monitoring system... {progress}% complete'
            
            if self.calibration_frames == 60:
                self.calibration_complete = True
                self.system_ready = True
                response['warning_message'] = '✅ Monitoring system ready'
            
            return response

        # Extract iris positions
        left_iris = np.array([mesh_coords[idx] for idx in self.LEFT_IRIS])
        right_iris = np.array([mesh_coords[idx] for idx in self.RIGHT_IRIS])
        
        (l_cx, l_cy), _ = cv2.minEnclosingCircle(left_iris)
        (r_cx, r_cy), _ = cv2.minEnclosingCircle(right_iris)

        # Calculate gaze metrics
        avg_iris_x = (l_cx + r_cx) / 2
        avg_iris_y = (l_cy + r_cy) / 2
        
        # Use baseline if available
        reference_x = self.baseline_nose_x if self.baseline_nose_x else frame_center_x
        
        horizontal_gaze_offset = abs(avg_iris_x - reference_x)
        vertical_gaze_offset = abs(avg_iris_y - frame_center_y)

        # Head position
        nose_x = mesh_coords[self.NOSE_TIP][0]
        nose_y = mesh_coords[self.NOSE_TIP][1]
        head_offset = abs(nose_x - reference_x)

        # MOVEMENT DETECTION - Track frame-to-frame changes
        movement_detected = False
        movement_magnitude = 0
        
        if self.prev_nose_pos is not None and self.prev_iris_pos is not None:
            # Calculate movement from previous frame
            nose_movement = np.sqrt((nose_x - self.prev_nose_pos[0])**2 + 
                                   (nose_y - self.prev_nose_pos[1])**2)
            iris_movement = np.sqrt((avg_iris_x - self.prev_iris_pos[0])**2 + 
                                   (avg_iris_y - self.prev_iris_pos[1])**2)
            
            movement_magnitude = max(nose_movement, iris_movement)
            
            # Add to movement history
            self.movement_history.append(movement_magnitude)
            if len(self.movement_history) > self.MOVEMENT_HISTORY_SIZE:
                self.movement_history.pop(0)
            
            # Check for excessive movement
            avg_movement = sum(self.movement_history) / len(self.movement_history) if self.movement_history else 0
            
            if movement_magnitude > self.EXCESSIVE_MOVEMENT_THRESHOLD:
                movement_detected = True
            elif avg_movement > self.MOVEMENT_THRESHOLD:
                movement_detected = True
        
        # Update previous positions
        self.prev_nose_pos = (nose_x, nose_y)
        self.prev_iris_pos = (avg_iris_x, avg_iris_y)

        # Detect distractions with LENIENT logic (less sensitive)
        is_distracted = False
        distraction_reason = ''
        
        # Priority 1: Excessive movement (most suspicious)
        if movement_detected and movement_magnitude > self.EXCESSIVE_MOVEMENT_THRESHOLD:
            is_distracted = True
            distraction_reason = '🚨 EXCESSIVE MOVEMENT DETECTED'
        
        # Priority 2: Horizontal gaze detection (looking left/right)
        elif horizontal_gaze_offset > self.GAZE_THRESHOLD:
            is_distracted = True
            direction = 'left' if avg_iris_x < reference_x else 'right'
            distraction_reason = f'⚠️ LOOKING {direction.upper()}'
        
        # Priority 3: Vertical gaze detection (looking up/down)
        elif vertical_gaze_offset > self.VERTICAL_GAZE_THRESHOLD:
            is_distracted = True
            direction = 'down' if avg_iris_y > frame_center_y else 'up'
            distraction_reason = f'⚠️ LOOKING {direction.upper()}'
        
        # Priority 4: Head movement detection
        elif head_offset > self.HEAD_MOVEMENT_THRESHOLD:
            is_distracted = True
            distraction_reason = '⚠️ HEAD TURNED AWAY'
        
        # Priority 5: Sustained movement (fidgeting/looking around)
        elif movement_detected:
            is_distracted = True
            distraction_reason = '⚠️ SUSPICIOUS MOVEMENT'
        
        # Handle distraction accumulation
        if is_distracted:
            if self.distraction_start_time is None:
                self.distraction_start_time = current_time
                # Show immediate feedback
                response['warning_message'] = distraction_reason
            else:
                distraction_duration = (current_time - self.distraction_start_time).total_seconds()
                if distraction_duration >= self.distraction_threshold:
                    response['warning_message'] = f'🛑 {distraction_reason} - WARNING ISSUED ({int(distraction_duration)}s)'
                    self._handle_warning('Looking Away')
                    self.distraction_start_time = current_time
                else:
                    # Show escalating urgency
                    response['warning_message'] = f'{distraction_reason} - {int(distraction_duration)}s'
        else:
            # Student is focused
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