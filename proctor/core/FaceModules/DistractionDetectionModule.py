import cv2
import mediapipe as mp
import numpy as np
from datetime import datetime


class DistractionDetector:
    """
    Enhanced distraction detection using iris tracking and head pose.
    """
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Landmark indices
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        self.LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        self.RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        
        # Detection thresholds
        self.GAZE_THRESHOLD = 50  # pixels
        self.HEAD_THRESHOLD = 100  # pixels
        self.BLINK_THRESHOLD = 0.2
        
        self.distraction_count = 0
        self.last_distraction_time = None
        self.consecutive_distractions = 0
        
    def calculate_eye_aspect_ratio(self, eye_landmarks, frame_width, frame_height):
        """Calculate the eye aspect ratio to detect blinks"""
        points = np.array([[int(point.x * frame_width), int(point.y * frame_height)] for point in eye_landmarks])
        
        # Compute the euclidean distances
        vertical_dist1 = np.linalg.norm(points[1] - points[5])
        vertical_dist2 = np.linalg.norm(points[2] - points[4])
        horizontal_dist = np.linalg.norm(points[0] - points[3])
        
        # Calculate eye aspect ratio
        ear = (vertical_dist1 + vertical_dist2) / (2.0 * horizontal_dist)
        return ear
        
    def detect_distraction(self, frame):
        frame_height, frame_width = frame.shape[:2]
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        is_distracted = False
        distraction_type = "Focused"
        
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            
            # Get mesh coordinates
            mesh_coords = [(int(point.x * frame_width), int(point.y * frame_height))
                          for point in face_landmarks.landmark]
            
            # Iris tracking
            (l_cx, l_cy), l_radius = cv2.minEnclosingCircle(
                np.array([mesh_coords[idx] for idx in self.LEFT_IRIS])
            )
            (r_cx, r_cy), r_radius = cv2.minEnclosingCircle(
                np.array([mesh_coords[idx] for idx in self.RIGHT_IRIS])
            )
            
            # Draw iris circles
            center_left = np.array([l_cx, l_cy], dtype=np.int32)
            center_right = np.array([r_cx, r_cy], dtype=np.int32)
            cv2.circle(frame, center_left, int(l_radius), (255, 0, 255), 1, cv2.LINE_AA)
            cv2.circle(frame, center_right, int(r_radius), (255, 0, 255), 1, cv2.LINE_AA)
            
            # Calculate gaze direction
            left_eye_offset = abs(l_cx - frame_center_x)
            right_eye_offset = abs(r_cx - frame_center_x)
            vertical_offset = abs((l_cy + r_cy) / 2 - frame_center_y)
            
            # Head position check
            nose = face_landmarks.landmark[1]
            nose_x = int(nose.x * frame_width)
            nose_y = int(nose.y * frame_height)
            head_offset = abs(nose_x - frame_center_x)
            
            # Blink detection
            left_eye_ratio = self.calculate_eye_aspect_ratio(
                [face_landmarks.landmark[idx] for idx in self.LEFT_EYE],
                frame_width, frame_height
            )
            right_eye_ratio = self.calculate_eye_aspect_ratio(
                [face_landmarks.landmark[idx] for idx in self.RIGHT_EYE],
                frame_width, frame_height
            )
            
            # Detect distractions
            if left_eye_offset > self.GAZE_THRESHOLD or right_eye_offset > self.GAZE_THRESHOLD:
                is_distracted = True
                distraction_type = "Looking Away"
            elif vertical_offset > self.GAZE_THRESHOLD:
                is_distracted = True
                distraction_type = "Looking Up/Down"
            elif head_offset > self.HEAD_THRESHOLD:
                is_distracted = True
                distraction_type = "Head Movement"
            elif left_eye_ratio < self.BLINK_THRESHOLD and right_eye_ratio < self.BLINK_THRESHOLD:
                is_distracted = True
                distraction_type = "Eyes Closed"
                
            # Update distraction stats
            current_time = datetime.now()
            if is_distracted:
                if self.last_distraction_time is None:
                    self.last_distraction_time = current_time
                    self.consecutive_distractions = 1
                else:
                    time_diff = (current_time - self.last_distraction_time).total_seconds()
                    if time_diff < 1.0:  # Consider continuous if less than 1 second apart
                        self.consecutive_distractions += 1
                    else:
                        self.consecutive_distractions = 1
                    self.last_distraction_time = current_time
                
                if self.consecutive_distractions >= 3:  # Three consecutive detections
                    self.distraction_count += 1
                    self.consecutive_distractions = 0
            else:
                self.consecutive_distractions = 0
                self.last_distraction_time = None
            
            # Display information on frame
            status_color = (0, 0, 255) if is_distracted else (0, 255, 0)
            cv2.putText(frame, f"Status: {distraction_type}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
            cv2.putText(frame, f"Distractions: {self.distraction_count}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Display eye tracking info
            cv2.putText(frame, f"Left offset: {int(left_eye_offset)}, Right offset: {int(right_eye_offset)}",
                       (10, frame_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame, is_distracted, distraction_type, self.distraction_count
        
    def reset_distraction_count(self):
        self.distraction_count = 0
        self.consecutive_distractions = 0
        self.last_distraction_time = None


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
        processed_frame, is_distracted, distraction_type, distraction_count = detector.detect_distraction(frame)
        
        # Show result
        cv2.imshow('Distraction Detection', processed_frame)
        
        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()