# MCQ Exam System Setup Guide

This guide explains how to set up and use the new MCQ exam functionality in the Proctoring System.

## Features

- **Real-time MCQ Exam Interface**: Students can take exams with actual questions from the database
- **Timer Functionality**: Automatic countdown timer with exam submission when time expires
- **Question Navigation**: Easy navigation between questions with visual indicators
- **Answer Tracking**: Visual feedback for answered questions
- **Automatic Scoring**: Automatic calculation and submission of exam scores
- **Responsive Design**: Works on desktop and mobile devices

## Setup Instructions

### 1. Database Setup

Make sure you have run the migrations to create the necessary database tables:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Create an Exam

1. Log in as a faculty member
2. Go to the faculty dashboard
3. Schedule a new exam with the following details:
   - Title: "Sample MCQ Exam"
   - Date: Set to current date/time
   - Duration: 15 minutes (or your preferred duration)
   - Description: "A sample MCQ exam for testing"

### 3. Add Questions to the Exam

Use the management command to add sample questions to your exam:

```bash
python manage.py add_sample_questions <exam_id>
```

Replace `<exam_id>` with the actual ID of the exam you created.

### 4. Test the MCQ Exam

1. Log in as a student
2. Go to "My Exams" page
3. Find your exam in the list
4. Click "Start Exam" button
5. The MCQ interface will load with all questions

## How It Works

### For Students

1. **Starting an Exam**: Click "Start Exam" on any ongoing exam
2. **Taking the Exam**:
   - Questions are displayed one at a time
   - Use the question numbers on the left to navigate
   - Select answers by clicking on options
   - Answered questions are marked with green indicators
   - Timer shows remaining time
3. **Submitting**: Click "Submit Exam" when finished or wait for time to expire

### For Faculty

1. **Creating Exams**: Use the existing exam scheduling interface
2. **Adding Questions**: Use the management command or create questions manually
3. **Viewing Results**: Check exam results through the existing results interface

## File Structure

- `proctor/core/views.py`: Contains `mcq_exam` and `submit_exam` views
- `proctor/core/urls.py`: URL patterns for MCQ exam functionality
- `proctor/core/templates/mcq.html`: The main MCQ exam interface
- `proctor/core/management/commands/add_sample_questions.py`: Command to add sample questions

## Technical Details

### Models Used

- `Exam`: Contains exam information (title, date, duration)
- `Question`: Contains individual MCQ questions with options
- `Submission`: Stores student exam submissions and scores

### Key Features

- **Real-time Timer**: JavaScript-based countdown with automatic submission
- **Answer Persistence**: Answers are stored in browser memory during the exam
- **Score Calculation**: Automatic scoring based on correct answers
- **CSRF Protection**: Secure form submission with CSRF tokens
- **Responsive Design**: Mobile-friendly interface

## Troubleshooting

### Common Issues

1. **No Questions Displayed**: Make sure you've added questions to the exam using the management command
2. **Timer Not Working**: Check browser console for JavaScript errors
3. **Submission Fails**: Ensure the exam hasn't ended and you haven't already submitted

### Debug Commands

```bash
# Check if questions exist for an exam
python manage.py shell
>>> from core.models import Exam, Question
>>> exam = Exam.objects.get(id=<exam_id>)
>>> print(f"Questions: {exam.questions.count()}")
```

## Future Enhancements

- Save answers periodically to prevent data loss
- Add proctoring features (face detection, screen recording)
- Implement question randomization
- Add support for different question types
- Create detailed analytics and reports 