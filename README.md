# SmartFace Proctor System

![SmartFace Proctor](https://img.shields.io/badge/Status-Active-success)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2.5-green)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive online examination proctoring system with AI-powered monitoring, automated cheating detection, and real-time analytics.

## ✨ Features

- **AI-Powered Proctoring**
  - Real-time face detection and tracking
  - Distraction detection (looking away, multiple faces, etc.)
  - Automated violation recording

- **Exam Management**
  - Create and schedule exams
  - Multiple question types (MCQ, True/False, etc.)
  - Time-based assessments

- **Auto-Save & Resume**
  - Answers saved every 30 seconds
  - Resume exams if disconnected
  - Manual/auto submission with accurate scoring

- **Faculty Dashboard**
  - Live monitoring of ongoing exams
  - View and manage violations
  - Manual exam control (pause/end/reset)

- **Student Portal**
  - Easy exam access
  - Intuitive interface
  - Real-time violation warnings

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- MySQL 8.0+
- Webcam
- Modern web browser

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/SmartFaceProctor.git
   cd SmartFaceProctor
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure database**
   - Create a MySQL database
   - Update `proctor/settings.py` with your database credentials:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.mysql',
             'NAME': 'your_database_name',
             'USER': 'your_username',
             'PASSWORD': 'your_password',
             'HOST': 'localhost',
             'PORT': '3306',
         }
     }
     ```

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open browser and go to: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## 🖥️ User Roles

### 1. Admin
- Full system access
- User management
- System configuration

### 2. Faculty
- Create and manage exams
- Monitor ongoing exams
- View student submissions
- Manage violations

### 3. Student
- Take scheduled exams
- View exam results
- Check violation history

## 🛠️ Technical Stack

- **Backend**: Django 5.2.5
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Database**: MySQL 8.0+
- **AI/ML**: OpenCV, MediaPipe, NumPy
- **Face Detection**: MediaPipe Face Mesh
- **Authentication**: Django Auth + Custom Middleware

## 📂 Project Structure

```
SmartFaceProctor/
├── proctor/                  # Main project directory
│   ├── core/                 # Main app
│   │   ├── migrations/       # Database migrations
│   │   ├── static/           # Static files (CSS, JS, images)
│   │   ├── templates/        # HTML templates
│   │   ├── FaceModules/      # AI/ML modules
│   │   ├── admin.py          # Admin configurations
│   │   ├── models.py         # Database models
│   │   ├── views.py          # View functions
│   │   └── ...
│   ├── proctor/              # Project settings
│   │   ├── settings.py       # Main settings
│   │   ├── urls.py          # Main URLs
│   │   └── ...
│   ├── manage.py             # Django management script
│   └── requirements.txt      # Project dependencies
├── docs/                    # Documentation
└── README.md                # This file
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_NAME=smartface_proctor
DATABASE_USER=db_user
DATABASE_PASSWORD=db_password
DATABASE_HOST=localhost
DATABASE_PORT=3306
```

### Google OAuth (Optional)
For Google Sheets integration:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Sheets API
4. Create OAuth 2.0 credentials
5. Download credentials as `credentials.json` to the project root

## 📊 Database Schema

Key models:
- **User**: Custom user model with role-based access
- **Exam**: Exam details and configuration
- **Question**: Exam questions and answers
- **Submission**: Student exam submissions
- **Violation**: Recorded proctoring violations
- **ExamProgress**: Auto-saved exam progress

## 🔄 Deployment

### Production
1. Set `DEBUG = False` in `settings.py`
2. Configure a production database
3. Set up a production web server (Nginx + Gunicorn recommended)
4. Configure static files:
   ```bash
   python manage.py collectstatic
   ```
5. Set up SSL certificates (Let's Encrypt recommended)

### Docker (Optional)
```bash
docker-compose up --build
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Contact

Project Link: [https://github.com/yourusername/SmartFaceProctor](https://github.com/yourusername/SmartFaceProctor)

## 🙏 Acknowledgments

- Django Documentation
- OpenCV and MediaPipe teams
- Bootstrap 5
- All contributors and testers

---

<div align="center">
  Made with ❤️ by Your Team Name
</div>
