// ...existing code...

class ExamMonitor {
    constructor() {
        this.videoElement = document.createElement('video');
        this.videoElement.style.display = 'none';
        document.body.appendChild(this.videoElement);
        this.canvas = document.createElement('canvas');
        this.distractionCheckInterval = 2000; // Check every 2 seconds
        this.lastCheck = Date.now();
    }

    async start() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            this.videoElement.srcObject = stream;
            await this.videoElement.play();
            
            this.canvas.width = this.videoElement.videoWidth;
            this.canvas.height = this.videoElement.videoHeight;
            
            setInterval(() => this.checkForDistractions(), this.distractionCheckInterval);
        } catch (error) {
            console.error('Camera access error:', error);
            alert('Camera access is required for exam monitoring');
        }
    }

    async checkForDistractions() {
        if (Date.now() - this.lastCheck < this.distractionCheckInterval) return;
        
        const context = this.canvas.getContext('2d');
        context.drawImage(this.videoElement, 0, 0);
        const frame = this.canvas.toDataURL('image/jpeg');

        try {
            const response = await fetch('/check-distraction/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    frame: frame,
                    exam_id: document.getElementById('exam-id').value
                })
            });

            const result = await response.json();
            if (result.is_distracted) {
                this.handleDistraction(result);
            }
        } catch (error) {
            console.error('Distraction check error:', error);
        }

        this.lastCheck = Date.now();
    }

    handleDistraction(result) {
        const notification = document.createElement('div');
        notification.className = 'distraction-warning';
        notification.textContent = `Warning: ${result.reason.join(', ')}`;
        document.body.appendChild(notification);
        
        setTimeout(() => notification.remove(), 3000);
        
        // Log violation
        this.logViolation(result);
    }

    async logViolation(result) {
        try {
            await fetch('/log-violation/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    exam_id: document.getElementById('exam-id').value,
                    violation_type: 'distraction',
                    details: result.reason.join(', '),
                    confidence: result.confidence
                })
            });
        } catch (error) {
            console.error('Error logging violation:', error);
        }
    }
}

// Initialize exam monitoring when page loads
document.addEventListener('DOMContentLoaded', () => {
    const examMonitor = new ExamMonitor();
    examMonitor.start();
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ...existing code...