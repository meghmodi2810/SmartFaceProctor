from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Exam, Submission, Violation
import cv2
import numpy as np
from django.utils import timezone
import mediapipe as mp
from django.contrib import messages
import os
import warnings
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from .models import Exam, Question, BugReport
from .Modules.SheetManagerModule import get_questions_from_sheet

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
	if request.method == 'POST':
		fullname = request.POST.get('fullname')
		username = request.POST.get('username')
		password1 = request.POST.get('password1')
		password2 = request.POST.get('password2')
		role = request.POST.get('role')

		if password1 != password2:
			messages.error(request, 'Passwords do not match.')
			return render(request, 'register.html')

		try:
			# Split fullname into first_name and last_name
			names = fullname.split(maxsplit=1)
			first_name = names[0]
			last_name = names[1] if len(names) > 1 else ''

			# Create the user
			from django.contrib.auth import get_user_model
			User = get_user_model()
			user = User.objects.create_user(
				username=username,
				email=username,  # Using username as email since it's required
				password=password1,
				first_name=first_name,
				last_name=last_name,
				role=role
			)
			messages.success(request, 'Registration successful! Please login.')
			return redirect('login')
		except Exception as e:
			messages.error(request, str(e))
			return render(request, 'register.html')

	return render(request, 'register.html')

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
	return render(request, 'exam_proctoring.html')

def logout_view(request):
	"""Enhanced logout with proper session cleanup"""
	if request.user.is_authenticated:
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
	warning_limit = request.POST.get('warningLimit')
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
	if validation_result['warnings']:
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
		
		# Create Exam
		exam = Exam.objects.create(
			title=title,
			date=date,
			duration_minutes=duration_minutes,
			created_by=request.user,
			sheet_url=sheet_url,
			description=f"Warning Limit: {warning_limit}"
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
	submissions = Submission.objects.filter(student=user)
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
	return render(request, 'facultydash.html', {
		'faculty': user
	})

@login_required
def faculty_exams(request):
	user = request.user
	if user.role != 'Faculty':
		return redirect('student_dashboard')
	exams_created = Exam.objects.filter(created_by=user).order_by('-date')
	return render(request, 'faculty_exams.html', {
		'faculty': user,
		'exams_created': exams_created
	})

@login_required
def schedule_exam_page(request):
	user = request.user
	if user.role != 'Faculty':
		return redirect('student_dashboard')
	return render(request, 'faculty_schedule.html', {
		'faculty': user
	})

@login_required
def faculty_profile(request):
	user = request.user
	if user.role != 'Faculty':
		return redirect('student_dashboard')
	return render(request, 'faculty_profile.html', {'faculty': user})

@login_required
def student_exams(request):
	user = request.user
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	
	# Get all exams and determine their status
	all_exams = Exam.objects.all().order_by('date')
	exams_with_status = []
	
	current_time = timezone.now()
	
	for exam in all_exams:
		exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
		
		if current_time < exam.date:
			status = 'upcoming'
		elif current_time >= exam.date and current_time <= exam_end_time:
			status = 'ongoing'
		elif current_time > exam_end_time:
			# Check if student has submitted
			submission = Submission.objects.filter(student=user, exam=exam).first()
			if submission:
				status = 'completed'
			else:
				status = 'expired'
		else:
			status = 'unknown'
		
		exam.status = status
		exams_with_status.append(exam)
	
	context = {
		'student': user,
		'exams': exams_with_status
	}
	return render(request, 'student_exams.html', context)

@login_required
def student_profile(request):
	user = request.user
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	
	return render(request, 'student_profile.html', {'student': user})

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
	if user.role != 'Student':
		return redirect('faculty_dashboard')
	
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
			return redirect('student_dashboard')
		else:
			messages.error(request, 'Please fill in all required fields.')
	
	return render(request, 'report_bug.html', {'student': user})

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
		return render(request, 'exam_review.html', {'exam': exam, 'submission': submission, 'student': user})
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
		
		# Final validation before starting exam
		current_time = timezone.now()
		exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
		
		if current_time < exam.date:
			messages.error(request, 'Exam has not started yet.')
			return redirect('mcq_exam', exam_id=exam_id)
		elif current_time > exam_end_time:
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
		
		# Prepare questions data for JavaScript (JSON)
		questions_data = []
		for question in questions:
			questions_data.append({
				'id': question.id,
				'text': question.text,
				'options': [
					question.option_a,
					question.option_b,
					question.option_c,
					question.option_d
				],
				'correct_answer': question.answer
			})
		
		context = {
			'exam': exam,
			'questions': questions,
			'questions_data': json.dumps(questions_data),
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
		data = json.loads(request.body)
		
		exam = Exam.objects.get(id=exam_id)
		
		# Check if exam is still ongoing
		current_time = timezone.now()
		exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
		
		if current_time > exam_end_time:
			return JsonResponse({'success': False, 'error': 'Exam has ended'})
		
		# Check if student has already submitted
		existing_submission = Submission.objects.filter(student=user, exam=exam).first()
		if existing_submission:
			return JsonResponse({'success': False, 'error': 'You have already submitted this exam'})
		
		# Create submission
		score = data.get('score', 0)
		submission = Submission.objects.create(
			exam=exam,
			student=user,
			score=score
		)
		
		return JsonResponse({'success': True, 'submission_id': submission.id})
		
	except Exam.DoesNotExist:
		return JsonResponse({'success': False, 'error': 'Exam not found'})
	except json.JSONDecodeError:
		return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
	except Exception as e:
		return JsonResponse({'success': False, 'error': str(e)})

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
