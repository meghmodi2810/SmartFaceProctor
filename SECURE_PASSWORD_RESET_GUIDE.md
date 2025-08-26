# Secure Password Reset System - Smart Face Proctor

## Overview

The Smart Face Proctor system now implements a secure, OTP-based password reset mechanism that significantly improves security compared to the previous system.

## Security Features

### 🔐 Multi-Step Verification
1. **Email Verification**: User must provide a registered email address
2. **OTP Authentication**: 6-digit One-Time Password sent via email
3. **Password Reset**: New password creation with confirmation

### 🛡️ Security Measures
- **OTP Expiration**: OTPs expire after 15 minutes
- **Rate Limiting**: Maximum 5 OTP attempts, 3 password attempts
- **Session Management**: Secure session handling with automatic cleanup
- **Password Strength**: Minimum 8 characters with strength validation
- **Single-Use OTPs**: Each OTP can only be used once

## How It Works

### Step 1: Request Password Reset
- User visits `/forget/` page
- Enters registered email address
- System validates email exists
- Generates and sends 6-digit OTP via email

### Step 2: Verify OTP
- User receives OTP email
- Enters OTP on `/verify-otp/` page
- System validates OTP and marks as used
- Redirects to password reset page

### Step 3: Set New Password
- User creates new password
- Confirms password
- System validates password strength
- Updates database and redirects to login

## Database Schema

### PasswordResetOTP Model
```python
class PasswordResetOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def is_expired(self):
        # OTP expires after 15 minutes
        return timezone.now() > self.created_at + timedelta(minutes=15)
```

## API Endpoints

| URL | Method | Description |
|-----|--------|-------------|
| `/forget/` | GET/POST | Request password reset and send OTP |
| `/verify-otp/` | GET/POST | Verify OTP code |
| `/reset-password/` | GET/POST | Set new password |

## Rate Limiting

### OTP Verification
- Maximum 5 attempts per email
- After 5 failures, user must request new OTP
- Attempts reset after successful verification

### Password Reset
- Maximum 3 attempts per email
- After 3 failures, user must start over
- Attempts reset after successful password change

## Email Templates

### OTP Email
```
Subject: Password Reset OTP - Smart Face Proctor

Hello [User Name],

You have requested to reset your password.

Your OTP (One-Time Password) is: [6-digit code]

This OTP is valid for 15 minutes only.
If you didn't request this password reset, please ignore this email.

Best regards,
Smart Face Proctor Team
```

## Management Commands

### Cleanup Expired OTPs
```bash
# Show what would be deleted
python manage.py cleanup_expired_otps --dry-run

# Actually delete expired OTPs
python manage.py cleanup_expired_otps
```

## Security Best Practices

### ✅ Implemented
- OTP expiration (15 minutes)
- Rate limiting on attempts
- Session-based security
- Password strength validation
- Single-use OTPs
- Automatic cleanup of expired data

### 🔒 Additional Recommendations
- Set up cron job to run cleanup command regularly
- Monitor failed attempts for security threats
- Log password reset activities
- Consider implementing CAPTCHA for high-traffic scenarios

## Migration Requirements

To implement this system, you need to:

1. **Create Migration**:
   ```bash
   python manage.py makemigrations
   ```

2. **Apply Migration**:
   ```bash
   python manage.py migrate
   ```

3. **Test the System**:
   - Test with valid email
   - Test with invalid email
   - Test OTP expiration
   - Test rate limiting
   - Test password strength validation

## Testing the System

### Test Cases
1. **Valid Flow**: Email → OTP → Password → Success
2. **Invalid Email**: Non-existent email should show error
3. **Expired OTP**: Wait 15+ minutes, OTP should be invalid
4. **Rate Limiting**: Multiple failed attempts should trigger limits
5. **Password Mismatch**: Different passwords should show error
6. **Weak Password**: Short password should be rejected

### Manual Testing Commands
```bash
# Test cleanup command
python manage.py cleanup_expired_otps --dry-run

# Check database for OTPs
python manage.py shell
>>> from core.models import PasswordResetOTP
>>> PasswordResetOTP.objects.all()
```

## Troubleshooting

### Common Issues
1. **OTP not received**: Check SMTP credentials and email configuration
2. **Session errors**: Ensure Django sessions are properly configured
3. **Database errors**: Verify migrations are applied correctly
4. **Rate limiting issues**: Check session configuration and storage

### Debug Commands
```bash
# Check Django settings
python manage.py check

# Verify database
python manage.py dbshell

# Test email configuration
python manage.py shell
>>> from core.Modules.send_email_using_sheets import SmartFaceProctorMailer
>>> mailer = SmartFaceProctorMailer()
>>> mailer.send_otp_email('test@example.com', '123456')
```

## Future Enhancements

### Potential Improvements
- SMS OTP as backup option
- Biometric authentication integration
- Two-factor authentication (2FA)
- Password history tracking
- Account lockout after suspicious activity
- Audit logging for security events

## Support

For technical support or questions about the secure password reset system, please refer to the system documentation or contact the development team.

---

**Note**: This system significantly improves security by implementing industry-standard OTP-based password reset mechanisms. Regular security audits and updates are recommended to maintain the highest level of protection. 