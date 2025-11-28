from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Exam, Submission, Violation, Department, User, ExamAttempt
import cv2
import numpy as np
from django.utils import timezone
import mediapipe as mp
from django.contrib import messages
import os
import warnings
from django.views.decorators.http import require_POST, require_http_methods
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Exam, Question, BugReport
from .Modules.SheetManagerModule import get_questions_from_sheet
import json
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from .FaceModules.DistractionDetectionModule import DistractionDetector
import base64
from io import BytesIO
from PIL import Image

distraction_detector = DistractionDetector()

def get_client_ip(request):
	"""Get the client's IP address"""
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		ip = x_forwarded_for.split(',')[0]
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0 = all messages, 1 = INFO, 2 = WARNING, 3 = ERROR
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

def home_redirect(request):
	return redirect('login')

def home(request):
    """Landing page view"""
    return render(request, 'homepage.html')

def login_view(request):
    # Check if user is already logged in
    if request.user.is_authenticated:
        # Redirect based on user role
        if request.user.role == 'Admin':
            return redirect('admin_dashboard')
        elif request.user.role == 'Student':
            return redirect('student_dashboard')
        elif request.user.role == 'Faculty':
            return redirect('faculty_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        # Rate limiting check
        login_attempts_key = f'login_attempts_{username}'
        login_attempts = request.session.get(login_attempts_key, 0)
        
        if login_attempts >= 5:
            messages.error(request, 'Too many failed login attempts. Please try again later.')
            return render(request, 'login.html')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                # Clear failed login attempts
                if login_attempts_key in request.session:
                    del request.session[login_attempts_key]
                
                # Regenerate session key for security
                request.session.cycle_key()
                
                login(request, user)
                
                # Set session expiry based on remember me
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(1800)  # 30 minutes
                
                # Initialize session security data
                import time
                request.session['session_start'] = time.time()
                request.session['last_activity'] = time.time()
                request.session['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
                request.session['ip_address'] = get_client_ip(request)
                request.session['login_count'] = request.session.get('login_count', 0) + 1
                request.session['user_role'] = user.role
                
                # Add success message
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                
                # Redirect based on user role
                if user.role == 'Admin':
                    return redirect('admin_dashboard')
                elif user.role == 'Student':
                    return redirect('student_dashboard')
                elif user.role == 'Faculty':
                    return redirect('faculty_dashboard')
                else:
                    messages.error(request, 'Invalid user role')
                    logout(request)
                    return redirect('login')
            else:
                messages.error(request, 'Your account has been deactivated. Please contact support.')
        else:
            # Increment failed login attempts
            request.session[login_attempts_key] = login_attempts + 1
            request.session.modified = True
            
            remaining_attempts = 5 - (login_attempts + 1)
            if remaining_attempts > 0:
                messages.error(request, f'Invalid credentials. {remaining_attempts} attempts remaining.')
            else:
                messages.error(request, 'Too many failed attempts. Please try again later.')
            
        return render(request, 'login.html')
    
    return render(request, 'login.html')

def register(request):
	"""Registration page with OTP verification and auto-generated credentials"""
	if request.method == 'POST':
		email = request.POST.get('email', '').strip()
		fullname = request.POST.get('fullname', '').strip()
		role = request.POST.get('role', '').strip()
		
		# Validate inputs
		if not email or not fullname or not role:
			messages.error(request, 'All fields are required.')
			return render(request, 'register.html')
		
		if role not in ['Student', 'Faculty']:
			messages.error(request, 'Invalid role selected.')
			return render(request, 'register.html')
		
		# Check if email already exists
		from django.contrib.auth import get_user_model
		User = get_user_model()
		if User.objects.filter(email=email).exists():
			messages.error(request, 'Email already registered.')
			return render(request, 'register.html')
		
		# Generate OTP
		import random
		otp = str(random.randint(100000, 999999))
		
		# Store OTP in database
		from .models import PasswordResetOTP
		PasswordResetOTP.objects.create(email=email, otp=otp)
		
		# Store registration data in session
		request.session['registration_email'] = email
		request.session['registration_fullname'] = fullname
		request.session['registration_role'] = role
		request.session.modified = True
		
		# Log OTP for debugging (visible in server logs)
		print(f"🔑 OTP for {email}: {otp}")
		
		# Send OTP email ASYNCHRONOUSLY using threading to prevent worker timeout
		import threading
		
		def send_otp_in_background():
			try:
				from django.core.mail import send_mail
				from django.conf import settings
				
				subject = "Smart Face Proctor - Email Verification OTP"
				message = f"""
Dear {fullname},

Thank you for registering with Smart Face Proctor!

Your OTP for email verification is: {otp}

This OTP is valid for 15 minutes.

If you did not request this registration, please ignore this email.

Best regards,
Smart Face Proctor Team
				"""
				
				print(f"📤 [Background Thread] Sending OTP email to {email}...")
				print(f"   FROM: {settings.DEFAULT_FROM_EMAIL}")
				
				result = send_mail(
					subject=subject,
					message=message,
					from_email=settings.DEFAULT_FROM_EMAIL,
					recipient_list=[email],
					fail_silently=False,
				)
				
				if result:
					print(f"✅ [Background Thread] Email sent successfully to {email}")
				else:
					print(f"❌ [Background Thread] send_mail returned 0 for {email}")
					
			except Exception as e:
				print(f"❌ [Background Thread] Email error for {email}: {str(e)}")
				import traceback
				traceback.print_exc()
		
		# Start email sending in background thread (daemon=False so it completes)
		email_thread = threading.Thread(target=send_otp_in_background, daemon=False)
		email_thread.start()
		
		# Redirect immediately without waiting for email
		messages.success(request, f'OTP has been sent to {email}. Please check your inbox (and spam folder) and verify to complete registration.')
		return redirect('verify_registration_otp')
	
	return render(request, 'register.html')

def verify_registration_otp(request):
	"""Verify OTP for registration"""
	email = request.session.get('registration_email')
	
	if not email:
		messages.error(request, 'Please start registration first.')
		return redirect('register')
	
	if request.method == 'POST':
		otp = request.POST.get('otp', '').strip()
		
		if not otp:
			messages.error(request, 'Please enter the OTP.')
			return render(request, 'verify_registration_otp.html', {'email': email})
		
		# Verify OTP
		from .models import PasswordResetOTP
		try:
			otp_record = PasswordResetOTP.objects.filter(
				email=email, 
				otp=otp, 
				is_used=False
			).order_by('-created_at').first()
			
			if not otp_record:
				messages.error(request, 'Invalid OTP.')
				return render(request, 'verify_registration_otp.html', {'email': email})
			
			if otp_record.is_expired():
				messages.error(request, 'OTP has expired. Please request a new one.')
				return redirect('register')
			
			# Mark OTP as used
			otp_record.is_used = True
			otp_record.save()
			
			# Generate username and password
			fullname = request.session.get('registration_fullname')
			role = request.session.get('registration_role')
			
			import random
			random_number = random.randint(1000000000, 9999999999)
			
			# Generate username based on role
			if role == 'Faculty':
				username = f'SPF-{random_number}'
			else:  # Student
				username = f'SPS-{random_number}'
			
			# Generate random password
			import string
			password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
			
			# Create user
			from django.contrib.auth import get_user_model
			User = get_user_model()
			
			# Split fullname into first_name and last_name
			names = fullname.split(maxsplit=1)
			first_name = names[0]
			last_name = names[1] if len(names) > 1 else ''
			
			user = User.objects.create_user(
				username=username,
				email=email,
				password=password,
				first_name=first_name,
				last_name=last_name,
				role=role
			)
			
			# Send credentials email
			try:
				subject = "Smart Face Proctor - Your Login Credentials"
				message = f"""
Dear {fullname},

Your registration has been completed successfully!

Your login credentials are:
Username: {username}
Password: {password}

Role: {role}

Please login at: {settings.SITE_URL}/login/

Important: Please change your password after first login for security.

Best regards,
Smart Face Proctor Team
				"""
				
				send_mail(
					subject=subject,
					message=message,
					from_email=settings.DEFAULT_FROM_EMAIL,
					recipient_list=[email],
					fail_silently=False,
				)
			except Exception as e:
				# Even if email fails, user is created
				pass
			
			# Clear session data
			for key in ['registration_email', 'registration_fullname', 'registration_role']:
				if key in request.session:
					del request.session[key]
			
			# Show credentials on success page
			request.session['new_username'] = username
			request.session['new_password'] = password
			request.session.modified = True
			
			return redirect('registration_success')
			
		except Exception as e:
			messages.error(request, f'Error during registration: {str(e)}')
			return render(request, 'verify_registration_otp.html', {'email': email})
	
	return render(request, 'verify_registration_otp.html', {'email': email})


def registration_success(request):
	"""Show registration success with credentials"""
	username = request.session.get('new_username')
	password = request.session.get('new_password')
	
	if not username or not password:
		return redirect('login')
	
	context = {
		'username': username,
		'password': password
	}
	
	# Clear credentials from session after displaying
	if 'new_username' in request.session:
		del request.session['new_username']
	if 'new_password' in request.session:
		del request.session['new_password']
	
	return render(request, 'registration_success.html', context)

def forget(request):
	if request.method == 'POST':
		email = request.POST.get('email')
		
		if email:
			try:
				print(f"=== DEBUG: Processing email: {email} ===")  # Debug
				
				# Check if user exists
				from .models import User
				try:
					user = User.objects.get(email=email)
					print(f"✓ User found: {user.username}")  # Debug
				except User.DoesNotExist:
					print(f"✗ User not found for email: {email}")  # Debug
					messages.error(request, 'No user found with this email address.')
					return render(request, 'forget.html')
				
				# Check if PasswordResetOTP model exists and can be used
				try:
					from .models import PasswordResetOTP
					print("✓ PasswordResetOTP model imported")  # Debug
					
					# Test if we can query the model
					test_count = PasswordResetOTP.objects.count()
					print(f"✓ Model query successful, current count: {test_count}")  # Debug
					
				except Exception as e:
					print(f"✗ PasswordResetOTP model error: {e}")  # Debug
					messages.error(request, f'Database model error: {str(e)}. Please run migrations.')
					return render(request, 'forget.html')
				
				# Clean up expired OTPs
				try:
					PasswordResetOTP.objects.filter(is_used=True).delete()
					expired_otps = PasswordResetOTP.objects.filter(is_used=False)
					for otp_obj in expired_otps:
						if otp_obj.is_expired():
							otp_obj.delete()
					print("✓ Cleanup completed")  # Debug
				except Exception as e:
					print(f"✗ Error in cleanup: {e}")  # Debug
					messages.error(request, f'Database error: {str(e)}')
					return render(request, 'forget.html')
				
				# Generate 6-digit OTP
				import random
				otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
				print(f"✓ Generated OTP: {otp}")  # Debug
				
				# Save OTP to database
				try:
					# Delete any existing OTPs for this email
					PasswordResetOTP.objects.filter(email=email).delete()
					# Create new OTP
					otp_obj = PasswordResetOTP.objects.create(email=email, otp=otp)
					print(f"✓ OTP saved to database: {otp_obj.id}")  # Debug
				except Exception as e:
					print(f"✗ Error saving OTP: {e}")  # Debug
					messages.error(request, f'Database error: {str(e)}')
					return render(request, 'forget.html')
				
				# Send OTP email
				try:
					from .Modules.send_email_using_sheets import SmartFaceProctorMailer
					mailer = SmartFaceProctorMailer()
					print("✓ Mailer created")  # Debug
					
					result = mailer.send_otp_email(email, otp)
					print(f"✓ Email result: {result}")  # Debug
				except Exception as e:
					print(f"✗ Error in email sending: {e}")  # Debug
					# Delete the OTP if email failed
					otp_obj.delete()
					messages.error(request, f'Email error: {str(e)}')
					return render(request, 'forget.html')
				
				if result['success']:
					print("✓ Email sent successfully, setting session and redirecting")  # Debug
					messages.success(request, result['message'])
					# Store email in session for next step
					request.session['reset_email'] = email
					request.session.modified = True  # Ensure session is saved
					print(f"✓ Session set: {request.session.get('reset_email')}")  # Debug
					
					# Force redirect to verify_otp
					from django.shortcuts import redirect
					response = redirect('verify_otp')
					print(f"✓ Redirect response created: {response}")  # Debug
					return response
				else:
					print(f"✗ Email failed: {result['error']}")  # Debug
					# Delete the OTP if email failed
					otp_obj.delete()
					messages.error(request, f"Failed to send OTP: {result['error']}")
					return render(request, 'forget.html')
					
			except Exception as e:
				print(f"✗ Exception in forget view: {str(e)}")  # Debug
				import traceback
				traceback.print_exc()  # Print full traceback
				messages.error(request, f'Error sending OTP: {str(e)}')
				return render(request, 'forget.html')
		else:
			messages.error(request, 'Please enter your email address.')
	
	return render(request, 'forget.html')

def verify_otp(request):
	# Check if email is in session
	email = request.session.get('reset_email')
	print(f"=== DEBUG verify_otp ===")  # Debug
	print(f"Session email: {email}")  # Debug
	print(f"All session keys: {list(request.session.keys())}")  # Debug
	
	if not email:
		print("✗ No email in session, redirecting to forget")  # Debug
		messages.error(request, 'Please request OTP first.')
		return redirect('forget')
	
	print(f"✓ Email found in session: {email}")  # Debug
	
	# Rate limiting: Check if too many attempts
	attempt_key = f'otp_attempts_{email}'
	attempts = request.session.get(attempt_key, 0)
	
	if attempts >= 5:
		messages.error(request, 'Too many failed attempts. Please request a new OTP.')
		# Clear session and redirect back to email entry
		if 'reset_email' in request.session:
			del request.session['reset_email']
		if attempt_key in request.session:
			del request.session[attempt_key]
		return redirect('forget')
	
	if request.method == 'POST':
		otp = request.POST.get('otp')
		
		if otp:
			try:
				from .models import PasswordResetOTP
				# Get the most recent OTP for this email
				otp_obj = PasswordResetOTP.objects.filter(email=email, is_used=False).first()
				
				if not otp_obj:
					messages.error(request, 'Invalid OTP. Please request a new one.')
					return redirect('forget')
				
				if otp_obj.is_expired():
					messages.error(request, 'OTP has expired. Please request a new one.')
					otp_obj.delete()
					return redirect('forget')
				
				if otp_obj.otp == otp:
					# OTP is valid, mark as used
					otp_obj.is_used = True
					otp_obj.save()
					# Clear attempt counter
					if attempt_key in request.session:
						del request.session[attempt_key]
					# Store email in session for password reset
					request.session['reset_email'] = email
					return redirect('reset_password')
				else:
					# Increment attempt counter
					request.session[attempt_key] = attempts + 1
					request.session.modified = True
					messages.error(request, f'Invalid OTP. {4 - attempts} attempts remaining.')
					
			except Exception as e:
				messages.error(request, f'Error verifying OTP: {str(e)}')
		else:
			messages.error(request, 'Please enter the OTP.')
	
	return render(request, 'verify_otp.html')

def reset_password(request):
	# Check if email is in session
	email = request.session.get('reset_email')
	if not email:
		messages.error(request, 'Please verify OTP first.')
		return redirect('forget')
	
	# Rate limiting: Check if too many attempts
	attempt_key = f'password_attempts_{email}'
	attempts = request.session.get(attempt_key, 0)
	
	if attempts >= 3:
		messages.error(request, 'Too many failed attempts. Please start over.')
		# Clear session and redirect back to email entry
		if 'reset_email' in request.session:
			del request.session['reset_email']
		if attempt_key in request.session:
			del request.session[attempt_key]
		return redirect('forget')
	
	if request.method == 'POST':
		password1 = request.POST.get('password1')
		password2 = request.POST.get('password2')
		
		if password1 and password2:
			if password1 != password2:
				# Increment attempt counter
				request.session[attempt_key] = attempts + 1
				request.session.modified = True
				messages.error(request, f'Passwords do not match. {2 - attempts} attempts remaining.')
				return render(request, 'reset_password.html')
			
			if len(password1) < 8:
				# Increment attempt counter
				request.session[attempt_key] = attempts + 1
				request.session.modified = True
				messages.error(request, f'Password must be at least 8 characters long. {2 - attempts} attempts remaining.')
				return render(request, 'reset_password.html')
			
			try:
				# Update user password
				from .models import User
				user = User.objects.get(email=email)
				user.set_password(password1)
				user.save()
				
				# Clear all session data
				if 'reset_email' in request.session:
					del request.session['reset_email']
				if attempt_key in request.session:
					del request.session[attempt_key]
				if f'otp_attempts_{email}' in request.session:
					del request.session[f'otp_attempts_{email}']
				
				messages.success(request, 'Password reset successfully! Please login with your new password.')
				return redirect('login')
				
			except User.DoesNotExist:
				messages.error(request, 'User not found.')
				return redirect('forget')
			except Exception as e:
				messages.error(request, f'Error resetting password: {str(e)}')
		else:
			messages.error(request, 'Please fill in all fields.')
	
	return render(request, 'reset_password.html')

def generate_frames():
	# Initialize MediaPipe Face Mesh with iris detection
	mp_face_mesh = mp.solutions.face_mesh
	face_mesh = mp_face_mesh.FaceMesh(
		max_num_faces=1,
		refine_landmarks=True,
		min_detection_confidence=0.5,
		min_tracking_confidence=0.5
	)
	
	mp_drawing = mp.solutions.drawing_utils
	
	cap = cv2.VideoCapture(0)

	while True:
		success, frame = cap.read()
		if not success:
			break
			
		# Flip the frame horizontally
		frame = cv2.flip(frame, 1)
		
		# Convert to RGB
		rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		
		# Process the image
		results = face_mesh.process(rgb_frame)
		
		if results.multi_face_landmarks:
			face_landmarks = results.multi_face_landmarks[0]
			
			# Get iris landmarks
			LEFT_IRIS = [474, 475, 476, 477]
			RIGHT_IRIS = [469, 470, 471, 472]
			
			# Get face mesh coordinates
			frame_height, frame_width = frame.shape[:2]
			mesh_coords = [(int(point.x * frame_width), int(point.y * frame_height))
						  for point in face_landmarks.landmark]
			
			# Draw circles for iris detection
			(l_cx, l_cy), l_radius = cv2.minEnclosingCircle(
				np.array([mesh_coords[idx] for idx in LEFT_IRIS])
			)
			(r_cx, r_cy), r_radius = cv2.minEnclosingCircle(
				np.array([mesh_coords[idx] for idx in RIGHT_IRIS])
			)
			
			center_left = np.array([l_cx, l_cy], dtype=np.int32)
			center_right = np.array([r_cx, r_cy], dtype=np.int32)
			
			# Draw the iris circles
			cv2.circle(frame, center_left, int(l_radius), (255, 0, 255), 1, cv2.LINE_AA)
			cv2.circle(frame, center_right, int(r_radius), (255, 0, 255), 1, cv2.LINE_AA)
			
			# Calculate gaze direction based on iris positions
			frame_center_x = frame_width / 2
			frame_center_y = frame_height / 2
			
			# Check if eyes are looking too far from center
			gaze_threshold = 50  # pixels
			left_eye_offset = abs(l_cx - frame_center_x)
			right_eye_offset = abs(r_cx - frame_center_x)
			vertical_offset = abs((l_cy + r_cy) / 2 - frame_center_y)
			
			# Check head position using nose tip (landmark 1)
			nose = face_landmarks.landmark[1]
			nose_x = int(nose.x * frame_width)
			nose_y = int(nose.y * frame_height)
			head_offset = abs(nose_x - frame_center_x)
			
			# Combined distraction detection
			if (left_eye_offset > gaze_threshold or 
				right_eye_offset > gaze_threshold or 
				vertical_offset > gaze_threshold or 
				head_offset > 100):  # head movement threshold
				status = "Distracted!"
				color = (0, 0, 255)  # Red
			else:
				status = "Focused"
				color = (0, 255, 0)  # Green
			
			# Display status
			cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
			
			# Display iris tracking info
			info_text = f"Left eye offset: {int(left_eye_offset)}, Right eye offset: {int(right_eye_offset)}"
			cv2.putText(frame, info_text, (10, frame_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

		# Encode frame for web stream
		ret, buffer = cv2.imencode('.jpg', frame)
		frame = buffer.tobytes()

		yield (b'--frame\r\n'
			   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def video_feed(request):
	return StreamingHttpResponse(generate_frames(),
		content_type='multipart/x-mixed-replace; boundary=frame')

@login_required
def exam_proctoring_page(request):
    exam_id = request.session.get('current_exam_id')
    
    try:
        exam = Exam.objects.get(id=exam_id)
        # Initialize a new detector for this exam session
        detector = DistractionDetector()
        detector.set_warning_threshold(exam.warning_limit)
        detector.set_absence_threshold(exam.absence_threshold)
        detector.set_distraction_threshold(exam.absence_threshold)  # Use same threshold for distraction
        
        return render(request, 'exam_proctoring.html', {
            'exam': exam,
            'warning_limit': exam.warning_limit,
            'absence_threshold': exam.absence_threshold,
            'freeze_duration': detector.freeze_duration
        })
        
    except Exam.DoesNotExist:
        messages.error(request, 'Exam not found.')
        return redirect('student_exams')

def logout_view(request):
    """Enhanced logout with proper session cleanup"""
    if request.user.is_authenticated:
        # Stop exam monitoring if active
        if request.session.get('monitoring_active'):
            try:
                from .FaceModules.exam_monitor import ExamMonitor
                exam_id = request.session.get('active_exam_id')
                if (exam_id):
                    monitor = ExamMonitor.get_instance(request.user.id, exam_id)
                    monitor.stop_monitoring()
            except Exception:
                pass  # Ensure logout continues even if monitoring cleanup fails
        
        # Log the logout activity
        user_name = request.user.username
        user_role = request.user.role
        
        # Clear session data
        request.session.flush()  # This removes all session data and regenerates session key
        
        # Perform logout
        logout(request)
        
        # Add logout message
        messages.success(request, f'You have been logged out successfully. Thank you, {user_name}!')
        
        # Redirect based on role for different login pages if needed
        if user_role == 'Admin':
            return redirect('admin_login')
        else:
            return redirect('login')
    else:
        return redirect('login')

@login_required
@require_POST
def schedule_exam(request):
	if request.user.role != 'Faculty':
		return JsonResponse({'error': 'Unauthorized'}, status=403)
	
	title = request.POST.get('examName')
	warning_limit = int(request.POST.get('warningLimit', 3))
	absence_threshold = int(request.POST.get('absenceThreshold', 10))
	exam_date = request.POST.get('examDate')
	exam_time = request.POST.get('examTime')
	freeze_time = request.POST.get('freezeTime')
	sheet_url = request.POST.get('sheetUrl')
	
	# Validate exam data
	from .Modules.ExamValidationModule import validate_exam_data
	validation_result = validate_exam_data(title, exam_date, exam_time, freeze_time, sheet_url)
	
	if not validation_result['is_valid']:
		# Return validation errors
		error_message = "Validation failed:\n" + "\n".join(validation_result['errors'])
		if validation_result['warnings']:
			error_message += "\n\nWarnings:\n" + "\n".join(validation_result['warnings'])
		messages.error(request, error_message)
		return HttpResponseRedirect(reverse('schedule_exam_page'))
	
	# If there are warnings, show them but continue
	if (validation_result['warnings']):
		warning_message = "Warnings:\n" + "\n".join(validation_result['warnings'])
		messages.warning(request, warning_message)
	
	try:
		# Combine date and time
		from datetime import datetime
		date_str = f"{exam_date} {exam_time}"
		naive_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
		# Make timezone-aware using the current timezone
		if timezone.is_naive(naive_date):
			current_tz = timezone.get_current_timezone()
			date = timezone.make_aware(naive_date, current_tz)
		else:
			date = naive_date
		duration_minutes = int(freeze_time)
		
		# Handle student selection
		student_selection = request.POST.get('student_selection', 'all')  # 'all', 'division', 'manual'
		is_selective = False
		
		# Create Exam with warning_limit and absence_threshold
		exam = Exam.objects.create(
			title=title,
			date=date,
			duration_minutes=duration_minutes,
			created_by=request.user,
			sheet_url=sheet_url,
			description=f"Warning Limit: {warning_limit}, Absence Threshold: {absence_threshold}s",
			is_selective=(student_selection != 'all'),
			warning_limit=warning_limit,
			absence_threshold=absence_threshold
		)
		
		# Extract and save questions
		questions = get_questions_from_sheet(sheet_url)
		for q in questions:
			Question.objects.create(
				exam=exam,
				text=q.get('Questions', ''),
				option_a=q.get('Option A', ''),
				option_b=q.get('Option B', ''),
				option_c=q.get('Option C', ''),
				option_d=q.get('Option D', ''),
				answer=q.get('Answer', '')
			)
		
		# Assign students based on selection
		from .models import User, ExamAssignment
		if student_selection == 'department':
			department_ids = request.POST.getlist('department_ids')
			if department_ids:
				students = User.objects.filter(role='Student', department_id__in=department_ids, is_active=True)
				for student in students:
					ExamAssignment.objects.get_or_create(
						exam=exam,
						student=student,
						defaults={'assigned_by': request.user, 'is_active': True}
					)
		elif student_selection == 'division':
			division_ids = request.POST.getlist('division_ids')
			if division_ids:
				students = User.objects.filter(role='Student', division_id__in=division_ids, is_active=True)
				for student in students:
					ExamAssignment.objects.get_or_create(
						exam=exam,
						student=student,
						defaults={'assigned_by': request.user, 'is_active': True}
					)
		elif student_selection == 'manual':
			student_ids = request.POST.getlist('student_ids')
			if student_ids:
				students = User.objects.filter(role='Student', id__in=student_ids, is_active=True)
				for student in students:
					ExamAssignment.objects.get_or_create(
						exam=exam,
						student=student,
						defaults={'assigned_by': request.user, 'is_active': True}
					)
		
		messages.success(request, f'Exam "{title}" scheduled successfully with {len(questions)} questions!')
		return HttpResponseRedirect(reverse('faculty_exams'))
		
	except Exception as e:
		messages.error(request, f'Error scheduling exam: {str(e)}')
		return HttpResponseRedirect(reverse('schedule_exam_page'))

@login_required
def schedule_exam_preview(request):
	if request.method != 'POST':
		return redirect('schedule_exam_page')
	if request.user.role != 'Faculty':
		return redirect('student_dashboard')
	# Collect form data
	title = request.POST.get('examName')
	warning_limit = request.POST.get('warningLimit')
	exam_date = request.POST.get('examDate')
	exam_time = request.POST.get('examTime')
	freeze_time = request.POST.get('freezeTime')
	sheet_url = request.POST.get('sheetUrl')
	# Validate and fetch questions
	from .Modules.ExamValidationModule import validate_exam_data
	validation_result = validate_exam_data(title, exam_date, exam_time, freeze_time, sheet_url)
	if not validation_result['is_valid']:
		error_message = "Validation failed:\n" + "\n".join(validation_result['errors'])
		if validation_result['warnings']:
			error_message += "\n\nWarnings:\n" + "\n".join(validation_result['warnings'])
		messages.error(request, error_message)
		return redirect('schedule_exam_page')
	# Fetch questions for preview
	try:
		questions = get_questions_from_sheet(sheet_url)
		# Normalize keys for template-safe access
		normalized_questions = []
		for q in questions:
			normalized_questions.append({
				'text': q.get('Questions', ''),
				'option_a': q.get('Option A', ''),
				'option_b': q.get('Option B', ''),
				'option_c': q.get('Option C', ''),
				'option_d': q.get('Option D', ''),
				'answer': q.get('Answer', '')
			})
	except Exception as e:
		messages.error(request, f'Error reading questions from sheet: {str(e)}')
		return redirect('schedule_exam_page')
	marks = len(questions)
	return render(request, 'faculty_schedule_preview.html', {
		'faculty': request.user,
		'preview': {
			'title': title,
			'warning_limit': warning_limit,
			'exam_date': exam_date,
			'exam_time': exam_time,
			'duration': freeze_time,
			'sheet_url': sheet_url,
			'questions': normalized_questions,
			'marks': marks,
			'question_count': len(questions)
		}
	})

@login_required
def delete_exam(request, exam_id):
	exam = Exam.objects.get(id=exam_id)
	if request.user != exam.created_by:
		return JsonResponse({'error': 'Unauthorized'}, status=403)
	exam.delete()
	messages.success(request, 'Exam deleted successfully!')
	return HttpResponseRedirect(reverse('faculty_exams'))

@login_required
def student_dashboard(request):
	user = request.user
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	upcoming_exams = Exam.objects.filter(date__gte=timezone.now()).order_by('date')
	submissions = Submission.objects.filter(student=user).order_by('-submitted_on')
	
	# Calculate grades for submissions
	from .views_student_results import calculate_grade
	for submission in submissions:
		submission.grade = calculate_grade(submission.score)
	
	violations = Violation.objects.filter(student=user)
	context = {
		'student': user,
		'upcoming_exams': upcoming_exams,
		'submissions': submissions,
		'violations': violations
	}
	return render(request, 'student_dashboard.html', context)

@login_required
def faculty_dashboard(request):
    user = request.user
    if user.role != 'Faculty':
        return redirect('student_dashboard')
        
    if not user.is_profile_complete:
        messages.info(request, 'Please complete your profile to continue.')
        return redirect('faculty_profile')
        
    return render(request, 'faculty_dashboard.html', {'faculty': user})

@login_required
def faculty_exams(request):
    user = request.user
    if user.role != 'Faculty':
        return redirect('student_dashboard')
    
    # Get all exams created by this faculty
    exams_created = Exam.objects.filter(created_by=user).order_by('-date')
    
    # Calculate status for each exam
    current_time = timezone.now()
    
    for exam in exams_created:
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        
        if current_time < exam.date:
            exam.status = 'upcoming'
        elif current_time >= exam.date and current_time <= exam_end_time:
            exam.status = 'ongoing'
        else:
            exam.status = 'completed'
    
    return render(request, 'faculty_exams.html', {
        'faculty': user,
        'exams_created': exams_created
    })

@login_required
def schedule_exam_page(request):
    """Display exam scheduling form with student selection options"""
    if request.user.role != 'Faculty':
        return redirect('student_dashboard')
    
    # Get all departments, divisions, and students for selection
    departments = Department.objects.filter(is_active=True).order_by('name')
    try:
        from .models import Division as _Division
        divisions = _Division.objects.filter(is_active=True).order_by('department', 'name')
    except Exception:
        divisions = []
    students = User.objects.filter(role='Student', is_active=True).select_related('department').order_by('first_name', 'last_name')
    
    context = {
        'departments': departments,
        'divisions': divisions,
        'students': students[:100],  # Limit to first 100 for performance
    }
    
    return render(request, 'faculty_schedule.html', context)

@login_required
def exam_feedback(request, exam_id):
    """Show feedback form after exam submission"""
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    try:
        exam = Exam.objects.get(id=exam_id)
        submission = Submission.objects.get(exam=exam, student=user)
        
        # Check if feedback already exists
        from .models import ExamFeedback
        existing_feedback = ExamFeedback.objects.filter(exam=exam, student=user).first()
        if existing_feedback:
            # Already submitted feedback, redirect to results
            return redirect('exam_results', exam_id=exam_id)
        
        context = {
            'exam': exam,
            'submission': submission,
            'student': user
        }
        return render(request, 'exam_feedback.html', context)
    except (Exam.DoesNotExist, Submission.DoesNotExist):
        messages.error(request, 'Exam or submission not found.')
        return redirect('student_exams')

@login_required
def submit_feedback(request, exam_id):
    """Handle feedback form submission"""
    if request.method != 'POST':
        return redirect('exam_feedback', exam_id=exam_id)
    
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    try:
        exam = Exam.objects.get(id=exam_id)
        rating = request.POST.get('rating')
        description = request.POST.get('description', '').strip()
        
        if not rating:
            messages.error(request, 'Please provide a rating.')
            return redirect('exam_feedback', exam_id=exam_id)
        
        # Create feedback
        from .models import ExamFeedback
        ExamFeedback.objects.create(
            exam=exam,
            student=user,
            rating=int(rating),
            description=description if description else None
        )
        
        messages.success(request, 'Thank you for your feedback!')
        return redirect('exam_results', exam_id=exam_id)
    except Exam.DoesNotExist:
        messages.error(request, 'Exam not found.')
        return redirect('student_exams')
    except Exception as e:
        messages.error(request, f'Error submitting feedback: {str(e)}')
        return redirect('exam_feedback', exam_id=exam_id)

@login_required
def exam_scheduling_guide(request):
    """Display guide on how to schedule exams using Google Sheets"""
    if request.user.role != 'Faculty':
        return redirect('student_dashboard')
    return render(request, 'exam_scheduling_guide.html')

@login_required
def download_template(request):
    """Download the QuestionsProctor.xlsx template"""
    if request.user.role != 'Faculty':
        return redirect('student_dashboard')
    
    import mimetypes
    from django.http import FileResponse
    
    # Path to template file
    template_path = os.path.join(os.path.dirname(__file__), 'excel_template', 'QuestionsProctor.xlsx')
    
    if not os.path.exists(template_path):
        messages.error(request, 'Template file not found.')
        return redirect('schedule_exam_page')
    
    # Open and return file
    response = FileResponse(open(template_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="QuestionsProctor.xlsx"'
    return response

@login_required
def faculty_profile(request):
    user = request.user
    if user.role != 'Faculty':
        return redirect('student_dashboard')
    
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        # Update profile information
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        # Don't allow email change
        # user.email = request.POST.get('email', '')
        user.dob = request.POST.get('dob')
        
        # Handle gender - convert full name to single character
        gender_input = request.POST.get('gender', '')
        if gender_input:
            if gender_input.lower() in ['male', 'm']:
                user.gender = 'M'
            elif gender_input.lower() in ['female', 'f']:
                user.gender = 'F'
            elif gender_input.lower() in ['other', 'o']:
                user.gender = 'O'
            else:
                user.gender = gender_input[0].upper() if len(gender_input) > 0 else None
        
        user.mobile_number = request.POST.get('mobile_number')
        user.address = request.POST.get('address')
        user.department_id = request.POST.get('department')
        user.specialization = request.POST.get('specialization')
        user.qualification = request.POST.get('qualification')
        
        # Handle department selection
        department_id = request.POST.get('department')
        if department_id:
            try:
                user.department = Department.objects.get(id=department_id, is_active=True)
            except Department.DoesNotExist:
                messages.error(request, 'Selected department is not valid.')
                return redirect('faculty_profile')
        
        # Check if essential fields are filled (simplified for faculty)
        required_fields = [
            user.first_name, user.last_name, user.email
        ]
        
        if all(required_fields):
            user.is_profile_complete = True
            user.save()
            messages.success(request, 'Profile updated successfully!')
            if request.POST.get('next'):
                return redirect(request.POST.get('next'))
        else:
            messages.warning(request, 'Please fill in name and email to complete your profile.')
    
    context = {
        'user': user,
        'departments': departments,
        'is_first_login': not user.is_profile_complete,
        'next': request.GET.get('next', 'faculty_dashboard')
    }
    return render(request, 'faculty_profile.html', context)

@login_required
def faculty_password_change(request):
    user = request.user
    if user.role != 'Faculty':
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password changed successfully. Please login again.')
            return redirect('login')
    
    return render(request, 'faculty_password_change.html', {'faculty': user})

@login_required
def faculty_results(request):
	user = request.user
	if user.role != 'Faculty':
		return redirect('student_dashboard')
	
	# Get all exams created by this faculty
	exams_qs = Exam.objects.filter(created_by=user).order_by('-date')
	
	# Optional search
	query = request.GET.get('q', '').strip()
	if query:
		exams_qs = exams_qs.filter(title__icontains=query)
	
	# Precompute stats efficiently
	from django.db.models import Count, Avg, Max, Min
	exams = list(exams_qs)
	exam_ids = [e.id for e in exams]
	stats = Submission.objects.filter(exam_id__in=exam_ids).values('exam_id').annotate(
		total_submissions=Count('id'),
		average_score=Avg('score'),
		highest_score=Max('score'),
		lowest_score=Min('score')
	)
	exam_id_to_stats = {s['exam_id']: s for s in stats}
	for e in exams:
		s = exam_id_to_stats.get(e.id, {})
		e.total_submissions = s.get('total_submissions', 0)
		e.average_score = s.get('average_score', 0) or 0
		e.highest_score = s.get('highest_score', 0) or 0
		e.lowest_score = s.get('lowest_score', 0) or 0
	
	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		# Return partial HTML for async update
		from django.template.loader import render_to_string
		html = render_to_string('partials/faculty_results_list.html', { 'exams': exams })
		return JsonResponse({ 'html': html })
	
	return render(request, 'faculty_results.html', {
		'faculty': user,
		'exams': exams,
		'query': query
	})

@login_required
def faculty_exam_results(request, exam_id):
	user = request.user
	if user.role != 'Faculty':
		return redirect('student_dashboard')
	
	try:
		exam = Exam.objects.get(id=exam_id, created_by=user)
		submissions = Submission.objects.filter(exam=exam).select_related('student').order_by('-score')
		
		# Calculate statistics
		total_students = submissions.count()
		if total_students > 0:
			average_score = submissions.aggregate(avg=models.Avg('score'))['avg']
			highest_score = submissions.aggregate(max=models.Max('score'))['max']
			lowest_score = submissions.aggregate(min=models.Min('score'))['min']
			
			# Pass/Fail analysis (assuming 40% is passing)
			passed = submissions.filter(score__gte=40).count()
			failed = total_students - passed
		else:
			average_score = 0
			highest_score = 0
			lowest_score = 0
			passed = 0
			failed = 0
		
		context = {
			'faculty': user,
			'exam': exam,
			'submissions': submissions,
			'stats': {
				'total_students': total_students,
				'average_score': round(average_score, 2) if average_score else 0,
				'highest_score': highest_score,
				'lowest_score': lowest_score,
				'passed': passed,
				'failed': failed,
				'pass_percentage': round((passed / total_students * 100), 2) if total_students > 0 else 0
			}
		}
		
		return render(request, 'faculty_exam_results.html', context)
		
	except Exam.DoesNotExist:
		messages.error(request, 'Exam not found or you do not have permission to view it.')
		return redirect('faculty_results')

@login_required
def generate_report_card(request, exam_id, student_id):
	user = request.user
	if user.role != 'Faculty':
		return redirect('student_dashboard')
	
	try:
		from django.http import HttpResponse
		from django.template.loader import render_to_string
		
		exam = Exam.objects.get(id=exam_id, created_by=user)
		from .models import User
		student = User.objects.get(id=student_id, role='Student')
		submission = Submission.objects.get(exam=exam, student=student)
		
		# Get all questions and student's performance
		questions = Question.objects.filter(exam=exam)
		total_questions = questions.count()
		
		# Calculate grade
		score = submission.score
		if score >= 90:
			grade = 'A+'
		elif score >= 80:
			grade = 'A'
		elif score >= 70:
			grade = 'B+'
		elif score >= 60:
			grade = 'B'
		elif score >= 50:
			grade = 'C'
		elif score >= 40:
			grade = 'D'
		else:
			grade = 'F'
		
		status = 'PASS' if score >= 40 else 'FAIL'
		
		context = {
			'exam': exam,
			'student': student,
			'submission': submission,
			'total_questions': total_questions,
			'grade': grade,
			'status': status,
			'faculty': user
		}
		
		return render(request, 'report_card.html', context)
		
	except (Exam.DoesNotExist, User.DoesNotExist, Submission.DoesNotExist):
		messages.error(request, 'Report card could not be generated.')
		return redirect('faculty_results')

@login_required
def student_exams(request):
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    from .models import ExamAssignment
    # Filter exams: if exam is_selective=True, only show if student is assigned
    # If is_selective=False (exam for all students), show to everyone
    all_exams = Exam.objects.select_related('created_by').only('id','title','date','duration_minutes','created_by_id','is_selective').order_by('-date')
    
    # Filter based on selective assignment
    if all_exams.exists():
        # Get IDs of exams where student is assigned (for selective exams)
        selective_exam_ids = set(ExamAssignment.objects.filter(
            student=user, exam_id__in=[e.id for e in all_exams], is_active=True
        ).values_list('exam_id', flat=True))
        
        # Show exams based on is_selective flag:
        # - is_selective=False: Show to ALL students (exam for all)
        # - is_selective=True: Show only if student is in selective_exam_ids
        filtered_exams = []
        for exam in all_exams:
            # Show if exam is NOT selective (available to all) OR student is assigned
            if exam.is_selective == False or exam.id in selective_exam_ids:
                filtered_exams.append(exam)
        all_exams = filtered_exams
    
    exams_with_status = []
    
    current_time = timezone.now()
    
    # Optional: paginate to speed up rendering for many exams
    try:
        from django.core.paginator import Paginator
        paginator = Paginator(all_exams, 15)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        exams_iterable = page_obj.object_list
    except Exception:
        exams_iterable = all_exams

    for exam in exams_iterable:
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        
        # Check if student has a submission
        submission = Submission.objects.filter(student=user, exam=exam).first()
        
        if current_time < exam.date:
            status = 'upcoming'
        elif current_time >= exam.date and current_time <= exam_end_time:
            # Exam time period is active
            if submission:
                # Student completed and submitted
                status = 'completed'
            else:
                # Exam is ongoing regardless of attempt status
                # (attempt blocking happens in exam view, not here)
                status = 'ongoing'
        elif current_time > exam_end_time:
            # Time has passed
            if submission:
                status = 'completed'
            else:
                status = 'expired'
        else:
            status = 'unknown'
        
        # Add required exam details
        exam.status = status
        exam.end_time = exam_end_time
        exam.questions_count = exam.questions.count()
        exam.start_time = exam.date
        exams_with_status.append(exam)
    
    context = {
        'student': user,
        'exams': exams_with_status,
        'page_obj': 'page_obj' in locals() and page_obj or None
    }
    return render(request, 'student_exams.html', context)

@login_required
def student_profile(request):
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    # Semester and division are OPTIONAL - don't load them by default
    # Admin can assign them if needed
    
    if request.method == 'POST':
        # Update profile information
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.dob = request.POST.get('dob')
        user.gender = request.POST.get('gender')
        user.mobile_number = request.POST.get('mobile_number')
        user.address = request.POST.get('address')
        user.branch = request.POST.get('branch')
        user.course = request.POST.get('course')
        user.current_semester = request.POST.get('current_semester')
        
        # Handle department selection (OPTIONAL - can be assigned by admin)
        department_id = request.POST.get('department')
        if department_id:
            try:
                user.department = Department.objects.get(id=department_id, is_active=True)
            except Department.DoesNotExist:
                pass  # Ignore invalid department, it's optional
        
        # Semester is OPTIONAL - students don't need to select it
        # Remove semester selection logic - admin manages this
        
        # Division is OPTIONAL - students don't need to select it
        # Remove division selection logic - admin manages this
        
        # Save profile
        user.save()
        
        # Check completion - only require name and email
        # Department, semester, division are OPTIONAL
        required_fields = [user.first_name, user.last_name, user.email]
        
        if all(required_fields):
            user.is_profile_complete = True
        else:
            user.is_profile_complete = False
        
        user.save()
        
        if user.is_profile_complete:
            messages.success(request, 'Profile updated successfully!')
        else:
            messages.warning(request, 'Please fill in your first name, last name, and email to complete your profile.')
    
    context = {
        'user': user,
        'departments': departments,
        'is_first_login': not user.is_profile_complete,
    }
    return render(request, 'student_profile.html', context)

@login_required
def student_password_change(request):
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password changed successfully. Please login again.')
            return redirect('login')
    
    return render(request, 'student_password_change.html')

@login_required
def student_profile_update(request):
    """Handle student profile updates and password changes"""
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
        
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    # Get semesters and divisions based on selected department
    semesters = []
    divisions = []
    try:
        from .models import Semester as _Semester, Division as _Division
        if user.department:
            semesters = _Semester.objects.filter(department=user.department, is_active=True).order_by('name')
            if getattr(user, 'semester', None):
                divisions = _Division.objects.filter(department=user.department, semester=user.semester, is_active=True).order_by('name')
            else:
                divisions = _Division.objects.filter(department=user.department, is_active=True).order_by('name')
    except Exception:
        pass
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            # Update profile information
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.dob = request.POST.get('dob')
            user.gender = request.POST.get('gender')
            user.mobile_number = request.POST.get('mobile_number')
            user.address = request.POST.get('address')
            user.branch = request.POST.get('branch')
            user.course = request.POST.get('course')
            user.current_semester = request.POST.get('current_semester')
            
            # Handle department selection
            department_id = request.POST.get('department')
            if department_id:
                try:
                    user.department = Department.objects.get(id=department_id, is_active=True)
                    # Update semesters and divisions when department changes
                    try:
                        from .models import Semester as _Semester, Division as _Division
                        semesters = _Semester.objects.filter(department=user.department, is_active=True).order_by('name')
                        divisions = _Division.objects.filter(department=user.department, is_active=True).order_by('name')
                    except Exception:
                        semesters = []
                        divisions = []
                except Department.DoesNotExist:
                    messages.error(request, 'Selected department is not valid.')
                    return redirect('student_profile_update')
            
            # Handle semester selection
            semester_id = request.POST.get('semester')
            if semester_id:
                try:
                    from .models import Semester as _Semester, Division as _Division
                    user.semester = _Semester.objects.get(id=semester_id, department=user.department, is_active=True)
                    # Update divisions based on selected semester
                    divisions = _Division.objects.filter(department=user.department, semester=user.semester, is_active=True).order_by('name')
                except Exception:
                    messages.error(request, 'Selected semester is not valid.')
            else:
                user.semester = None
            
            # Handle division selection
            division_id = request.POST.get('division')
            if division_id:
                try:
                    from .models import Division as _Division
                    user.division = _Division.objects.get(id=division_id, department=user.department, is_active=True)
                except Exception:
                    messages.error(request, 'Selected division is not valid.')
            else:
                user.division = None
            
            # Save profile first
            user.save()
            
            # Check completion - only require basic fields for students
            required_fields = [
                user.first_name, user.last_name, user.email, user.department
            ]
            
            if all(required_fields):
                user.is_profile_complete = True
            else:
                user.is_profile_complete = False
            
            user.save()
            
            if user.is_profile_complete:
                messages.success(request, 'Profile updated successfully!')
            else:
                messages.warning(request, 'Please fill in name, email, and department to complete your profile.')
        
        elif action == 'change_password':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not user.check_password(old_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password changed successfully. Please login again.')
                return redirect('login')
    
    context = {
        'user': user,
        'departments': departments,
        'is_first_login': not user.is_profile_complete,
    }
    return render(request, 'student_profile_update.html', context)

@login_required
def start_exam(request, exam_id):
	user = request.user
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	
	try:
		exam = Exam.objects.get(id=exam_id)
		return render(request, 'exam_proctoring.html', {'exam': exam})
	except Exam.DoesNotExist:
		messages.error(request, 'Exam not found.')
		return redirect('student_exams')

@login_required
def report_bug(request):
	user = request.user
	
	if request.method == 'POST':
		bug_type = request.POST.get('bug_type')
		priority = request.POST.get('priority')
		title = request.POST.get('title')
		description = request.POST.get('description')
		browser = request.POST.get('browser')
		
		if bug_type and priority and title and description:
			BugReport.objects.create(
				reporter=user,
				bug_type=bug_type,
				priority=priority,
				title=title,
				description=description,
				browser=browser
			)
			messages.success(request, 'Bug report submitted successfully!')
			# Redirect based on user role
			if user.role == 'Faculty':
				return redirect('faculty_dashboard')
			else:
				return redirect('student_exams')
		else:
			messages.error(request, 'Please fill in all required fields.')
	
	return render(request, 'report_bug.html', {'student': user, 'user': user})

@login_required
def exam_instructions(request, exam_id):
	user = request.user
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	
	try:
		exam = Exam.objects.get(id=exam_id)
		return render(request, 'exam_instructions.html', {'exam': exam, 'student': user})
	except Exam.DoesNotExist:
		messages.error(request, 'Exam not found.')
		return redirect('student_exams')

@login_required
def exam_results(request, exam_id):
	user = request.user
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	
	try:
		exam = Exam.objects.get(id=exam_id)
		submission = Submission.objects.filter(student=user, exam=exam).first()
		if not submission:
			messages.error(request, 'No submission found for this exam.')
			return redirect('student_exams')
		return render(request, 'exam_results.html', {'exam': exam, 'submission': submission, 'student': user})
	except Exam.DoesNotExist:
		messages.error(request, 'Exam not found.')
		return redirect('student_exams')

@login_required
def exam_review(request, exam_id):
	user = request.user
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	
	try:
		exam = Exam.objects.get(id=exam_id)
		submission = Submission.objects.filter(student=user, exam=exam).first()
		if not submission:
			messages.error(request, 'No submission found for this exam.')
			return redirect('student_exams')
		
		# Get all questions for this exam
		questions = Question.objects.filter(exam=exam).order_by('id')
		
		# Get student's answers from ExamProgress (if exists)
		from .models import ExamProgress
		progress = ExamProgress.objects.filter(exam=exam, student=user).first()
		student_answers = progress.answers if progress else {}
		
		# Build detailed question analysis
		question_analysis = []
		correct_count = 0
		incorrect_count = 0
		unattempted_count = 0
		
		for idx, question in enumerate(questions, 1):
			student_answer = student_answers.get(str(question.id), '')
			correct_answer = question.answer
			
			is_correct = False
			is_attempted = bool(student_answer)
			
			if is_attempted:
				is_correct = (student_answer == correct_answer)
				if is_correct:
					correct_count += 1
				else:
					incorrect_count += 1
			else:
				unattempted_count += 1
			
			question_analysis.append({
				'number': idx,
				'question': question,
				'student_answer': student_answer,
				'correct_answer': correct_answer,
				'is_correct': is_correct,
				'is_attempted': is_attempted,
				'options': {
					'A': question.option_a,
					'B': question.option_b,
					'C': question.option_c,
					'D': question.option_d,
				}
			})
		
		# Calculate grade
		from .views_student_results import calculate_grade
		grade = calculate_grade(submission.score)
		
		context = {
			'exam': exam,
			'submission': submission,
			'student': user,
			'question_analysis': question_analysis,
			'total_questions': questions.count(),
			'correct_count': correct_count,
			'incorrect_count': incorrect_count,
			'unattempted_count': unattempted_count,
			'grade': grade,
			'accuracy': round((correct_count / questions.count() * 100), 1) if questions.count() > 0 else 0
		}
		
		return render(request, 'exam_review.html', context)
	except Exam.DoesNotExist:
		messages.error(request, 'Exam not found.')
		return redirect('student_exams')

@login_required
def mcq_exam(request, exam_id):
	user = request.user
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	
	try:
		exam = Exam.objects.get(id=exam_id)
		questions = Question.objects.filter(exam=exam).order_by('id')
		
		# Check exam status
		current_time = timezone.now()
		exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
		
		# Determine exam status
		if current_time < exam.date:
			# Exam hasn't started yet - show waiting page
			context = {
				'exam': exam,
				'exam_start_iso': exam.date.isoformat(),
				'questions_count': questions.count(),
				'student': user
			}
			return render(request, 'exam_waiting.html', context)
		elif current_time > exam_end_time:
			# Exam has ended
			messages.error(request, 'This exam has ended.')
			return redirect('student_exams')
		
		# Check if student has already submitted
		existing_submission = Submission.objects.filter(student=user, exam=exam).first()
		if existing_submission:
			messages.error(request, 'You have already submitted this exam.')
			return redirect('exam_results', exam_id=exam_id)
		
		# Check if exam has questions
		if not questions.exists():
			messages.error(request, 'This exam has no questions available.')
			return redirect('student_exams')
		
		# Exam is ready to start - show validation page first
		context = {
			'exam': exam,
			'questions': questions,
			'questions_count': questions.count(),
			'student': user,
			'exam_duration': exam.duration_minutes,
			'exam_end_time': exam_end_time,
			'exam_status': 'ready'
		}
		
		return render(request, 'exam_validation.html', context)
		
	except Exam.DoesNotExist:
		messages.error(request, 'Exam not found.')
		return redirect('student_exams')

@login_required
def start_mcq_exam(request, exam_id):
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    try:
        import json
        exam = Exam.objects.get(id=exam_id)
        questions = Question.objects.filter(exam=exam).order_by('id')
        
        # Check exam status
        current_time = timezone.now()
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        
        # Check if exam has ended
        if current_time > exam_end_time:
            messages.error(request, 'This exam has ended.')
            return redirect('student_exams')
        
        # Check if exam hasn't started yet
        if current_time < exam.date:
            context = {
                'exam': exam,
                'exam_start_iso': exam.date.isoformat(),
                'questions_count': questions.count(),
                'student': user
            }
            return render(request, 'exam_waiting.html', context)
        
        # Check if student has already submitted
        existing_submission = Submission.objects.filter(student=user, exam=exam).first()
        if existing_submission:
            # Show error on exam page with redirect option
            context = {
                'exam': exam,
                'error_message': 'You have already submitted this exam.',
                'redirect_url': f'/student/exam-results/{exam_id}/',
                'redirect_text': 'View Results',
                'student': user
            }
            return render(request, 'exam_error.html', context)
        
        # Check if exam has questions
        if not questions.exists():
            context = {
                'exam': exam,
                'error_message': 'This exam has no questions available.',
                'redirect_url': '/student/exams/',
                'redirect_text': 'Back to Exams',
                'student': user
            }
            return render(request, 'exam_error.html', context)

        # Check if student has already attempted the exam
        from .models import ExamAttempt
        existing_attempt = ExamAttempt.objects.filter(exam=exam, student=user).first()
        if existing_attempt and not existing_attempt.can_reattempt:
            context = {
                'exam': exam,
                'error_message': 'You have already attempted this exam. Contact faculty if you need to reattempt.',
                'redirect_url': '/student/exams/',
                'redirect_text': 'Back to Exams',
                'student': user
            }
            return render(request, 'exam_error.html', context)

        # Create exam attempt record
        if existing_attempt:
            # Re-attempting - reset the record
            existing_attempt.can_reattempt = False
            existing_attempt.save()
        else:
            # First attempt - create new record
            ExamAttempt.objects.create(exam=exam, student=user)

        # Store monitoring session info in user's session
        # Note: ExamMonitor initialization is deferred to avoid slow page load
        request.session['active_exam_id'] = exam_id
        request.session['monitoring_active'] = True
        
        context = {
            'exam': exam,
            'questions': questions,
            'student': user,
            'exam_duration': exam.duration_minutes,
            'exam_end_time': exam_end_time.isoformat()
        }
        
        return render(request, 'mcq.html', context)
        
    except Exam.DoesNotExist:
        messages.error(request, 'Exam not found.')
        return redirect('student_exams')

@login_required
def submit_exam(request, exam_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    user = request.user
    if user.role != 'Student':
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in submit_exam: {e}")
            return JsonResponse({'success': False, 'error': 'Invalid request data'})
        
        exam = Exam.objects.get(id=exam_id)
        
        # Check if exam is still ongoing
        current_time = timezone.now()
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        if current_time > exam_end_time:
            logger.warning(f"Student {user.id} tried to submit exam {exam_id} after it ended")
            return JsonResponse({'success': False, 'error': 'Exam has ended'})
        
        # Check if student has already submitted
        existing_submission = Submission.objects.filter(student=user, exam=exam).first()
        if existing_submission:
            logger.warning(f"Student {user.id} tried to submit exam {exam_id} twice")
            return JsonResponse({'success': False, 'error': 'You have already submitted this exam'})
        
        # Get answers from request
        answers = data.get('answers', {})
        
        # **FIX: Save answers to ExamProgress BEFORE calculating score**
        from .models import ExamProgress
        try:
            progress, created = ExamProgress.objects.update_or_create(
                exam=exam,
                student=user,
                defaults={'answers': answers}
            )
            logger.info(f"Answers saved to ExamProgress: {len(answers)} questions")
        except Exception as e:
            logger.error(f"Error saving to ExamProgress: {e}")
            # Continue anyway - don't fail submission
        
        # Calculate score based on correct answers
        questions = Question.objects.filter(exam=exam)
        correct_count = 0
        total_questions = questions.count()
        attempted_count = 0
        
        for question in questions:
            student_answer = answers.get(str(question.id), '')
            if student_answer:  # Count only if student provided an answer
                attempted_count += 1
                if student_answer == question.answer:
                    correct_count += 1
        
        # Calculate percentage score based on total questions (not attempted)
        if total_questions > 0:
            score = (correct_count / total_questions * 100)
        else:
            score = 0
        
        # Create submission
        try:
            submission = Submission.objects.create(
                exam=exam,
                student=user,
                score=score
            )
            logger.info(f"Submission created: student={user.id}, exam={exam_id}, score={score}, correct={correct_count}/{total_questions}")
        except Exception as e:
            logger.error(f"Error creating submission: {e}")
            return JsonResponse({'success': False, 'error': 'Failed to save submission'})
        
        # Mark exam attempt as completed
        try:
            exam_attempt = ExamAttempt.objects.filter(exam=exam, student=user, is_active=True).first()
            if exam_attempt:
                exam_attempt.is_active = False
                exam_attempt.ended_at = timezone.now()
                exam_attempt.save()
                logger.info(f"ExamAttempt marked as completed for student {user.id}")
        except Exception as e:
            logger.error(f"Error updating exam attempt: {e}")
            # Don't fail the submission if attempt update fails

        # Stop the exam monitoring if it exists
        try:
            from .FaceModules.exam_monitor import ExamMonitor
            monitor = ExamMonitor.get_instance(user.id, exam_id)
            if monitor:
                monitor.stop_monitoring()
        except Exception:
            pass  # Monitor might not exist, continue anyway
        
        # Clear monitoring session data and detector state
        session_key = f'detector_{user.id}_{exam_id}'
        if session_key in request.session:
            del request.session[session_key]
        if 'active_exam_id' in request.session:
            del request.session['active_exam_id']
        if 'monitoring_active' in request.session:
            del request.session['monitoring_active']
        request.session.modified = True
        
        logger.info(f"Submission successful: student={user.id}, exam={exam_id}, score={score}")
        
        return JsonResponse({
            'success': True, 
            'submission_id': submission.id,
            'score': score,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'redirect_url': f'/exam-feedback/{exam_id}/'
        })
        
    except Exam.DoesNotExist:
        logger.error(f"Exam not found: {exam_id}")
        return JsonResponse({'success': False, 'error': 'Exam not found'})
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON data in submit_exam")
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Unexpected error in submit_exam: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})

@login_required
def save_progress(request):
    """Save student's partial exam answers (auto-save)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    user = request.user
    if user.role != 'Student':
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        answers = data.get('answers', {})
        
        if not exam_id:
            return JsonResponse({'success': False, 'error': 'Exam ID required'})
        
        # Get exam
        exam = Exam.objects.get(id=exam_id)
        
        # Check if exam is still ongoing
        current_time = timezone.now()
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        if current_time > exam_end_time:
            return JsonResponse({'success': False, 'error': 'Exam has ended'})
        
        # Import ExamProgress model
        from .models import ExamProgress
        
        # Update or create progress
        progress, created = ExamProgress.objects.update_or_create(
            exam=exam,
            student=user,
            defaults={'answers': answers}
        )
        
        logger.info(f"Progress saved: student={user.id}, exam={exam_id}, questions={len(answers)}")
        
        return JsonResponse({
            'success': True,
            'saved_questions': len(answers),
            'last_updated': progress.last_updated.isoformat()
        })
        
    except Exam.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Exam not found'})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error saving progress: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Failed to save progress'})

def test_otp_system(request):
	"""Test view to debug OTP system"""
	if request.method == 'POST':
		email = request.POST.get('email')
		if email:
			try:
				# Test user lookup
				from .models import User
				try:
					user = User.objects.get(email=email)
					print(f"✓ User found: {user.username}")
				except User.DoesNotExist:
					print(f"✗ User not found for email: {email}")
					return JsonResponse({'error': 'User not found'})
				
				# Test if PasswordResetOTP model exists
				try:
					from .models import PasswordResetOTP
					print("✓ PasswordResetOTP model imported successfully")
				except ImportError as e:
					print(f"✗ Failed to import PasswordResetOTP model: {e}")
					return JsonResponse({'error': f'Model import failed: {e}'})
				
				# Test OTP creation
				import random
				otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
				try:
					otp_obj = PasswordResetOTP.objects.create(email=email, otp=otp)
					print(f"✓ OTP created: {otp_obj.id}")
				except Exception as e:
					print(f"✗ Failed to create OTP: {e}")
					return JsonResponse({'error': f'OTP creation failed: {e}'})
				
				# Test email sending
				try:
					from .Modules.send_email_using_sheets import SmartFaceProctorMailer
					mailer = SmartFaceProctorMailer()
					print("✓ Mailer created successfully")
				except Exception as e:
					print(f"✗ Failed to create mailer: {e}")
					# Clean up OTP
					otp_obj.delete()
					return JsonResponse({'error': f'Mailer creation failed: {e}'})
				
				try:
					result = mailer.send_otp_email(email, otp)
					print(f"✓ Email result: {result}")
				except Exception as e:
					print(f"✗ Failed to send email: {e}")
					# Clean up OTP
					otp_obj.delete()
					return JsonResponse({'error': f'Email sending failed: {e}'})
				
				# Clean up test OTP
				otp_obj.delete()
				
				return JsonResponse({
					'success': True,
					'result': result,
					'message': 'OTP system test completed'
				})
				
			except Exception as e:
				print(f"✗ Exception in test: {str(e)}")
				import traceback
				traceback.print_exc()
				return JsonResponse({'error': str(e)})
	
	return render(request, 'test_otp.html')

def check_database(request):
	"""Simple view to check database models"""
	if request.method == 'POST':
		try:
			from .models import User, PasswordResetOTP
			
			# Check User model
			user_count = User.objects.count()
			
			# Check PasswordResetOTP model
			try:
				otp_count = PasswordResetOTP.objects.count()
				otp_status = f"✓ PasswordResetOTP model exists, {otp_count} records"
			except Exception as e:
				otp_status = f"✗ PasswordResetOTP model error: {e}"
			
			# Check if we can create a test OTP
			try:
				test_otp = PasswordResetOTP.objects.create(
					email="test@example.com", 
					otp="123456"
				)
				test_otp.delete()  # Clean up
				otp_create_status = "✓ Can create and delete OTP records"
			except Exception as e:
				otp_create_status = f"✗ Cannot create OTP records: {e}"
			
			return JsonResponse({
				'success': True,
				'user_count': user_count,
				'otp_status': otp_status,
				'otp_create_status': otp_create_status
			})
			
		except Exception as e:
			return JsonResponse({
				'success': False,
				'error': str(e)
			})
	
	return render(request, 'check_db.html')

def get_semesters_api(request):
    """API endpoint to get semesters for a department"""
    from django.http import JsonResponse
    department_id = request.GET.get('department_id')
    
    if not department_id:
        return JsonResponse({'error': 'department_id is required'}, status=400)
    
    try:
        department = Department.objects.get(id=department_id, is_active=True)
        try:
            from .models import Semester as _Semester
            semesters = _Semester.objects.filter(department=department, is_active=True).order_by('name')
            semesters_data = [{'id': s.id, 'name': s.name} for s in semesters]
        except Exception:
            semesters_data = []
        return JsonResponse({'semesters': semesters_data})
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_divisions_api(request):
    """API endpoint to get divisions for a department (optionally filtered by semester)"""
    from django.http import JsonResponse
    department_id = request.GET.get('department_id')
    semester_id = request.GET.get('semester_id')
    
    if not department_id:
        return JsonResponse({'error': 'department_id is required'}, status=400)
    
    try:
        department = Department.objects.get(id=department_id, is_active=True)
        try:
            from .models import Division as _Division
            divisions_query = _Division.objects.filter(department=department, is_active=True)
            if semester_id:
                divisions_query = divisions_query.filter(semester_id=semester_id)
            divisions = divisions_query.order_by('name')
            divisions_data = [{'id': d.id, 'name': d.name} for d in divisions]
        except Exception:
            divisions_data = []
        return JsonResponse({'divisions': divisions_data})
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_migration(request):
	"""Check if PasswordResetOTP model exists in database"""
	try:
		from django.db import connection
		from django.db.utils import OperationalError
		
		# Check if the table exists
		with connection.cursor() as cursor:
			cursor.execute("""
				SELECT COUNT(*) 
				FROM information_schema.tables 
				WHERE table_schema = DATABASE() 
				AND table_name = 'core_passwordresetotp'
			""")
			table_exists = cursor.fetchone()[0] > 0
		
		if table_exists:
			# Try to import and use the model
			try:
				from .models import PasswordResetOTP
				count = PasswordResetOTP.objects.count()
				return JsonResponse({
					'success': True,
					'message': 'PasswordResetOTP model exists and is working',
					'table_exists': True,
					'record_count': count
				})
			except Exception as e:
				return JsonResponse({
					'success': False,
					'message': 'Table exists but model has errors',
					'table_exists': True,
					'error': str(e)
				})
		else:
			return JsonResponse({
				'success': False,
				'message': 'PasswordResetOTP table does not exist. Run migrations first.',
				'table_exists': False
			})
			
	except Exception as e:
		return JsonResponse({
			'success': False,
			'message': f'Error checking database: {str(e)}'
		})

@login_required
def edit_exam(request, exam_id):
    user = request.user
    if user.role != 'Faculty':
        return redirect('student_dashboard')
    
    try:
        exam = Exam.objects.get(id=exam_id)
        if request.user != exam.created_by:
            messages.error(request, 'You can only edit your own exams.')
            return redirect('faculty_exams')
            
        if request.method == 'POST':
            title = request.POST.get('examName')
            warning_limit = request.POST.get('warningLimit')
            exam_date = request.POST.get('examDate')
            exam_time = request.POST.get('examTime')
            duration_minutes = request.POST.get('duration')
            sheet_url = request.POST.get('sheetUrl')
            
            from datetime import datetime
            exam_datetime = datetime.strptime(f"{exam_date} {exam_time}", "%Y-%m-%d %H:%M")
            
            if timezone.is_naive(exam_datetime):
                current_tz = timezone.get_current_timezone()
                exam_datetime = timezone.make_aware(exam_datetime, current_tz)
            
            exam.title = title
            exam.description = f"Warning Limit: {warning_limit}"
            exam.date = exam_datetime
            exam.duration_minutes = int(duration_minutes)
            exam.sheet_url = sheet_url
            exam.save()
            
            messages.success(request, 'Exam updated successfully!')
            return redirect('faculty_exams')
            
        context = {
            'faculty': user,
            'exam': exam,
            'exam_date': exam.date.strftime('%Y-%m-%d'),
            'exam_time': exam.date.strftime('%H:%M'),
            'warning_limit': exam.description.split(': ')[-1] if exam.description else ''
        }
        return render(request, 'faculty_edit_exam.html', context)
        
    except Exam.DoesNotExist:
        messages.error(request, 'Exam not found.')
        return redirect('faculty_exams')

@login_required
def check_exam_status(request, exam_id):
    """Check if an exam has started and is ready to begin"""
    user = request.user
    if user.role != 'Student':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        exam = Exam.objects.get(id=exam_id)
        current_time = timezone.now()
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        
        # Check if exam has started
        if current_time < exam.date:
            return JsonResponse({'started': False, 'message': 'Exam has not started yet'})
        elif current_time > exam_end_time:
            return JsonResponse({'started': False, 'message': 'Exam has ended'})
            
        # Check if student has already submitted
        existing_submission = Submission.objects.filter(student=user, exam=exam).first()
        if existing_submission:
            return JsonResponse({'started': False, 'message': 'You have already submitted this exam'})
            
        # Exam is ready to start
        return JsonResponse({'started': True})
        
    except Exam.DoesNotExist:
        return JsonResponse({'error': 'Exam not found'}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def process_frame(request):
    try:
        data = json.loads(request.body)
        frame_data = data.get('frame')
        exam_id = data.get('exam_id')
        
        if not frame_data:
            return JsonResponse({
                'success': False,
                'error': 'No frame data provided'
            }, status=400)

        # Remove the data URL prefix to get the base64 string
        frame_base64 = frame_data.split(',')[1]
        
        # Convert base64 to image
        image_data = base64.b64decode(frame_base64)
        image = Image.open(BytesIO(image_data))
        
        # Convert PIL image to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Get exam warning settings
        warning_limit = 3  # default
        absence_threshold = 5  # default
        if exam_id:
            try:
                exam = Exam.objects.get(id=exam_id)
                warning_desc = exam.description or ""
                if "Warning Limit:" in warning_desc:
                    warning_limit = int(warning_desc.split("Warning Limit:")[1].strip())
            except (Exam.DoesNotExist, ValueError, IndexError):
                pass

        # Get or create detector instance for this exam session
        detector_key = f'detector_{request.user.id}_{exam_id}'
        if not hasattr(request, detector_key):
            detector = DistractionDetector()
            detector.set_warning_threshold(warning_limit)
            detector.set_absence_threshold(absence_threshold)
            detector.set_distraction_threshold(absence_threshold)  # Use same threshold for distraction
            setattr(request, detector_key, detector)
        else:
            detector = getattr(request, detector_key)

        # Process frame
        processed_frame, is_distracted, distractions = detector.is_distracted(opencv_image)
        
        # Check for multiple faces
        if len(detector.face_mesh.process(cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)).multi_face_landmarks or []) > 1:
            distractions.append("Multiple faces detected")
            is_distracted = True

        warning_message = ", ".join(distractions) if distractions else ""
        
        # Record violation if there are distractions
        if exam_id and is_distracted and request.user.is_authenticated:
            violation_type = 'Face Missing' if 'Face not detected' in warning_message else 'Distraction'
            details = warning_message or 'Unknown distraction'
            Violation.objects.create(
                exam_id=exam_id,
                student=request.user,
                type=violation_type,
                details=details
            )
        
        # Convert processed frame back to base64 for response
        _, buffer = cv2.imencode('.jpg', processed_frame)
        processed_frame_base64 = base64.b64encode(buffer).decode('utf-8')

        return JsonResponse({
            'success': True,
            'processed_frame': f'data:image/jpeg;base64,{processed_frame_base64}',
            'is_distracted': is_distracted,
            'warning_message': warning_message,
            'warning_count': len(distractions) if distractions else 0
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def check_distraction(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        frame_data = data.get('frame')
        exam_id = data.get('exam_id')
        warning_limit = data.get('warning_limit', 3)
        absence_threshold = data.get('absence_threshold', 10)
        
        if not frame_data:
            return JsonResponse({'error': 'No frame data provided'}, status=400)
        
        # Convert base64 frame to cv2 image
        encoded_data = frame_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Get or create detector instance for this user's exam session
        session_key = f'detector_{request.user.id}_{exam_id}'
        
        # Get detector state from session or initialize
        detector_state = request.session.get(session_key, {
            'warning_count': 0,
            'is_frozen': False,
            'freeze_start_time': None,
            'warning_limit': 3,
            'absence_threshold': 10,
            'distraction_start_time': None,
            'last_face_detected_time': None,
            # NEW: Movement tracking state
            'prev_nose_pos': None,
            'prev_iris_pos': None,
            'movement_history': [],
            'calibration_frames': 0,
            'baseline_nose_x': None,
            'baseline_iris_x': None
        })
        
        # Create detector and restore state
        detector = DistractionDetector()
        
        # Get exam settings and check if exam is still ongoing
        if exam_id:
            try:
                exam = Exam.objects.get(id=exam_id)
                
                # Check if exam has ended - if so, clear state and return
                exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
                if timezone.now() > exam_end_time:
                    # Exam has ended - clear session state
                    if session_key in request.session:
                        del request.session[session_key]
                        request.session.modified = True
                    return JsonResponse({
                        'success': False,
                        'exam_ended': True,
                        'message': 'Exam has ended'
                    })
                
                detector.set_warning_threshold(exam.warning_limit)
                detector.set_absence_threshold(exam.absence_threshold)
                detector.set_distraction_threshold(exam.absence_threshold)  # Use same threshold for distraction
                detector_state['warning_limit'] = exam.warning_limit
                detector_state['absence_threshold'] = exam.absence_threshold
            except Exam.DoesNotExist:
                detector.set_warning_threshold(warning_limit)
                detector.set_absence_threshold(absence_threshold)
                detector.set_distraction_threshold(absence_threshold)  # Use same threshold for distraction
        else:
            detector.set_warning_threshold(warning_limit)
            detector.set_absence_threshold(absence_threshold)
            detector.set_distraction_threshold(absence_threshold)
        
        # Check if faculty has cancelled freeze for this student
        if exam_id and detector_state.get('is_frozen', False):
            try:
                exam = Exam.objects.get(id=exam_id)
                # Check if there are any frozen violations that have been cancelled by faculty
                cancelled_freeze = Violation.objects.filter(
                    exam=exam,
                    student=request.user,
                    is_frozen=False,  # Changed from True to False by faculty
                    freeze_cancelled_by__isnull=False
                ).exists()
                
                if cancelled_freeze:
                    # Faculty has cancelled the freeze - unfreeze immediately
                    detector_state['is_frozen'] = False
                    detector_state['freeze_start_time'] = None
                    print(f"Freeze cancelled by faculty for student {request.user.id}")
            except Exam.DoesNotExist:
                pass
        
        # Restore detector state from session
        detector.warning_count = detector_state.get('warning_count', 0)
        detector.is_exam_frozen = detector_state.get('is_frozen', False)
        
        # Restore time-based tracking
        if detector_state.get('freeze_start_time'):
            from datetime import datetime
            detector.freeze_start_time = datetime.fromisoformat(detector_state['freeze_start_time'])
        
        if detector_state.get('distraction_start_time'):
            from datetime import datetime
            detector.distraction_start_time = datetime.fromisoformat(detector_state['distraction_start_time'])
        
        if detector_state.get('last_face_detected_time'):
            from datetime import datetime
            detector.last_face_detected_time = datetime.fromisoformat(detector_state['last_face_detected_time'])
        
        if detector_state.get('last_warning_time'):
            from datetime import datetime
            detector.last_warning_time = datetime.fromisoformat(detector_state['last_warning_time'])
        
        # Restore movement tracking state
        if detector_state.get('prev_nose_pos'):
            detector.prev_nose_pos = tuple(detector_state['prev_nose_pos'])
        if detector_state.get('prev_iris_pos'):
            detector.prev_iris_pos = tuple(detector_state['prev_iris_pos'])
        detector.movement_history = detector_state.get('movement_history', [])
        
        # Restore calibration data
        detector.calibration_frames = detector_state.get('calibration_frames', 0)
        detector.baseline_nose_x = detector_state.get('baseline_nose_x')
        detector.baseline_iris_x = detector_state.get('baseline_iris_x')
        
        # Process frame for distractions
        result = detector.detect_distraction(frame)
        
        # Save updated detector state back to session
        request.session[session_key] = {
            'warning_count': detector.warning_count,
            'is_frozen': detector.is_exam_frozen,
            'freeze_start_time': detector.freeze_start_time.isoformat() if detector.freeze_start_time else None,
            'distraction_start_time': detector.distraction_start_time.isoformat() if detector.distraction_start_time else None,
            'last_face_detected_time': detector.last_face_detected_time.isoformat() if detector.last_face_detected_time else None,
            'last_warning_time': detector.last_warning_time.isoformat() if detector.last_warning_time else None,
            'warning_limit': detector.warning_limit,
            'absence_threshold': detector.absence_threshold,
            # Save movement tracking state
            'prev_nose_pos': list(detector.prev_nose_pos) if detector.prev_nose_pos else None,
            'prev_iris_pos': list(detector.prev_iris_pos) if detector.prev_iris_pos else None,
            'movement_history': detector.movement_history,
            # Save calibration data
            'calibration_frames': detector.calibration_frames,
            'baseline_nose_x': detector.baseline_nose_x,
            'baseline_iris_x': detector.baseline_iris_x
        }
        request.session.modified = True
        
        # Log violation if warning issued
        if result.get('warning_message') and exam_id and request.user.is_authenticated:
            try:
                exam = Exam.objects.get(id=exam_id)
                violation_type = 'Face Missing' if 'Face not detected' in result['warning_message'] else 'Distraction'
                
                # Only create violation on new warnings to avoid duplicates
                # Check if we've incremented warning count in this call
                previous_count = detector_state.get('warning_count', 0)
                if result.get('warning_count', 0) > previous_count:
                    violation = Violation.objects.create(
                        exam=exam,
                        student=request.user,
                        type=violation_type,
                        is_frozen=result.get('is_frozen', False)
                    )
                    print(f"Violation logged: {violation_type}, Warning {result.get('warning_count')}/{exam.warning_limit}")
            except Exam.DoesNotExist:
                pass
        
        return JsonResponse(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

def detect_face(frame):
    # Use existing face detection logic from DistractionDetector
    try:
        from .FaceModules.DistractionDetectionModule import DistractionDetector
        detector = DistractionDetector()
        result = detector.detect_distraction(frame)
        return result.get('face_detected', False)
    except Exception:
        # Fallback to basic face detection if module import fails
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        return len(faces) > 0

@csrf_exempt
def log_violation(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        violation_type = data.get('violation_type', 'Distraction')
        details = data.get('details', '')
        
        if not exam_id:
            return JsonResponse({'error': 'Exam ID is required'}, status=400)
        
        # Get exam
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return JsonResponse({'error': 'Exam not found'}, status=404)
        
        # Create violation record
        Violation.objects.create(
            exam=exam,
            student=request.user,
            type=violation_type
        )
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

def test_otp_system(request):
	"""Test view to debug OTP system"""
	if request.method == 'POST':
		email = request.POST.get('email')
		if email:
			try:
				# Test user lookup
				from .models import User
				try:
					user = User.objects.get(email=email)
					print(f"✓ User found: {user.username}")
				except User.DoesNotExist:
					print(f"✗ User not found for email: {email}")
					return JsonResponse({'error': 'User not found'})
				
				# Test if PasswordResetOTP model exists
				try:
					from .models import PasswordResetOTP
					print("✓ PasswordResetOTP model imported successfully")
				except ImportError as e:
					print(f"✗ Failed to import PasswordResetOTP model: {e}")
					return JsonResponse({'error': f'Model import failed: {e}'})
				
				# Test OTP creation
				import random
				otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
				try:
					otp_obj = PasswordResetOTP.objects.create(email=email, otp=otp)
					print(f"✓ OTP created: {otp_obj.id}")
				except Exception as e:
					print(f"✗ Failed to create OTP: {e}")
					return JsonResponse({'error': f'OTP creation failed: {e}'})
				
				# Test email sending
				try:
					from .Modules.send_email_using_sheets import SmartFaceProctorMailer
					mailer = SmartFaceProctorMailer()
					print("✓ Mailer created successfully")
				except Exception as e:
					print(f"✗ Failed to create mailer: {e}")
					# Clean up OTP
					otp_obj.delete()
					return JsonResponse({'error': f'Mailer creation failed: {e}'})
				
				try:
					result = mailer.send_otp_email(email, otp)
					print(f"✓ Email result: {result}")
				except Exception as e:
					print(f"✗ Failed to send email: {e}")
					# Clean up OTP
					otp_obj.delete()
					return JsonResponse({'error': f'Email sending failed: {e}'})
				
				# Clean up test OTP
				otp_obj.delete()
				
				return JsonResponse({
					'success': True,
					'result': result,
					'message': 'OTP system test completed'
				})
				
			except Exception as e:
				print(f"✗ Exception in test: {str(e)}")
				import traceback
				traceback.print_exc()
				return JsonResponse({'error': str(e)})
	
	return render(request, 'test_otp.html')

def check_database(request):
	"""Simple view to check database models"""
	if request.method == 'POST':
		try:
			from .models import User, PasswordResetOTP
			
			# Check User model
			user_count = User.objects.count()
			
			# Check PasswordResetOTP model
			try:
				otp_count = PasswordResetOTP.objects.count()
				otp_status = f"✓ PasswordResetOTP model exists, {otp_count} records"
			except Exception as e:
				otp_status = f"✗ PasswordResetOTP model error: {e}"
			
			# Check if we can create a test OTP
			try:
				test_otp = PasswordResetOTP.objects.create(
					email="test@example.com", 
					otp="123456"
				)
				test_otp.delete()  # Clean up
				otp_create_status = "✓ Can create and delete OTP records"
			except Exception as e:
				otp_create_status = f"✗ Cannot create OTP records: {e}"
			
			return JsonResponse({
				'success': True,
				'user_count': user_count,
				'otp_status': otp_status,
				'otp_create_status': otp_create_status
			})
			
		except Exception as e:
			return JsonResponse({
				'success': False,
				'error': str(e)
			})
	
	return render(request, 'check_db.html')

def get_semesters_api(request):
    """API endpoint to get semesters for a department"""
    from django.http import JsonResponse
    department_id = request.GET.get('department_id')
    
    if not department_id:
        return JsonResponse({'error': 'department_id is required'}, status=400)
    
    try:
        department = Department.objects.get(id=department_id, is_active=True)
        try:
            from .models import Semester as _Semester
            semesters = _Semester.objects.filter(department=department, is_active=True).order_by('name')
            semesters_data = [{'id': s.id, 'name': s.name} for s in semesters]
        except Exception:
            semesters_data = []
        return JsonResponse({'semesters': semesters_data})
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_divisions_api(request):
    """API endpoint to get divisions for a department (optionally filtered by semester)"""
    from django.http import JsonResponse
    department_id = request.GET.get('department_id')
    semester_id = request.GET.get('semester_id')
    
    if not department_id:
        return JsonResponse({'error': 'department_id is required'}, status=400)
    
    try:
        department = Department.objects.get(id=department_id, is_active=True)
        try:
            from .models import Division as _Division
            divisions_query = _Division.objects.filter(department=department, is_active=True)
            if semester_id:
                divisions_query = divisions_query.filter(semester_id=semester_id)
            divisions = divisions_query.order_by('name')
            divisions_data = [{'id': d.id, 'name': d.name} for d in divisions]
        except Exception:
            divisions_data = []
        return JsonResponse({'divisions': divisions_data})
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_migration(request):
	"""Check if PasswordResetOTP model exists in database"""
	try:
		from django.db import connection
		from django.db.utils import OperationalError
		
		# Check if the table exists
		with connection.cursor() as cursor:
			cursor.execute("""
				SELECT COUNT(*) 
				FROM information_schema.tables 
				WHERE table_schema = DATABASE() 
				AND table_name = 'core_passwordresetotp'
			""")
			table_exists = cursor.fetchone()[0] > 0
		
		if table_exists:
			# Try to import and use the model
			try:
				from .models import PasswordResetOTP
				count = PasswordResetOTP.objects.count()
				return JsonResponse({
					'success': True,
					'message': 'PasswordResetOTP model exists and is working',
					'table_exists': True,
					'record_count': count
				})
			except Exception as e:
				return JsonResponse({
					'success': False,
					'message': 'Table exists but model has errors',
					'table_exists': True,
					'error': str(e)
				})
		else:
			return JsonResponse({
				'success': False,
				'message': 'PasswordResetOTP table does not exist. Run migrations first.',
				'table_exists': False
			})
			
	except Exception as e:
		return JsonResponse({
			'success': False,
			'message': f'Error checking database: {str(e)}'
		})

@login_required
def search_exams(request):
    user = request.user
    if user.role != 'Faculty':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    query = request.GET.get('q', '').strip()
    min_score = request.GET.get('min_score')
    max_score = request.GET.get('max_score')
    
    exams = Exam.objects.filter(created_by=user).order_by('-date')
    
    # Filter by title if query exists
    if query:
        exams = exams.filter(title__icontains=query)
    
    # Add submission statistics for each exam
    results = []
    for exam in exams:
        submissions = Submission.objects.filter(exam=exam)
        avg_score = submissions.aggregate(avg=models.Avg('score'))['avg'] or 0
        
        # Filter by score range if provided
        if min_score and float(min_score) > avg_score:
            continue
        if max_score and float(max_score) < avg_score:
            continue
            
        results.append({
            'id': exam.id,
            'title': exam.title,
            'date': exam.date.strftime('%B %d, %Y at %H:%M'),
            'total_submissions': submissions.count(),
            'average_score': round(avg_score, 1),
            'highest_score': submissions.aggregate(max=models.Max('score'))['max'] or 0,
            'lowest_score': submissions.aggregate(min=models.Min('score'))['min'] or 0,
        })
    
    return JsonResponse({'exams': results})