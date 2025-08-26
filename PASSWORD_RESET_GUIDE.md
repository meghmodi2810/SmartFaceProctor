# Password Reset System Guide

This guide explains the new password reset functionality that keeps existing user IDs but generates new passwords.

## Overview

The password reset system has been updated to:
- **Keep existing user IDs**: Students and faculty retain their original IDs
- **Generate new passwords**: Only the password is changed during reset
- **Send email notifications**: Users receive their ID and new password via email

## How It Works

### For Users (Students/Faculty)

1. **Access Password Reset**:
   - Go to the login page
   - Click "Forgot password?" link
   - Enter your registered email address
   - Click "Reset Password"

2. **Receive Email**:
   - Check your email inbox
   - You'll receive an email with:
     - Your existing ID (username)
     - Your new password
   - Example email content:
   ```
   Hello John Doe,
   
   Your password has been reset successfully.
   
   Your login credentials:
   ID: SPS-1234567890
   New Password: aB3xK9mN2pQ7
   
   Please login with these credentials and change your password after login.
   
   Best regards,
   Smart Face Proctor Team
   ```

3. **Login with New Credentials**:
   - Use your existing ID
   - Use the new password from the email
   - Login successfully

### For Administrators

The system automatically:
- Validates the email address exists in the database
- Generates a secure 12-character password
- Updates the user's password in the database
- Sends the email with ID and new password
- Provides success/error feedback

## Technical Implementation

### Files Modified

1. **`proctor/core/views.py`**:
   - Updated `forget()` view to handle password reset
   - Uses the mailer class for email functionality

2. **`proctor/core/templates/forget.html`**:
   - Complete redesign with modern UI
   - Form for email input
   - Success/error message display

3. **`proctor/core/Modules/send_email_using_sheets.py`**:
   - Added `generate_new_password()` method
   - Added `reset_user_password()` method
   - Added `send_password_reset_email()` method
   - Enhanced error handling

4. **`proctor/core/management/commands/test_password_reset.py`**:
   - New command for testing password reset functionality

### Key Methods

#### `reset_user_password(email)`
- Finds user by email
- Generates new password
- Updates user's password in database
- Returns success/error status

#### `send_password_reset_email(email)`
- Calls `reset_user_password()`
- Sends email with ID and new password
- Handles email delivery errors

#### `generate_new_password()`
- Creates secure 12-character password
- Uses letters and numbers
- Ensures password security

## Testing

### Using Management Command

Test the password reset functionality:

```bash
python manage.py test_password_reset user@example.com
```

### Manual Testing

1. Create a test user in the database
2. Go to `/forget/` page
3. Enter the user's email
4. Check if email is received
5. Try logging in with new credentials

## Security Features

- **Email Validation**: Only registered emails can reset passwords
- **Secure Passwords**: 12-character random passwords with letters and numbers
- **Database Updates**: Passwords are properly hashed using Django's password system
- **Error Handling**: Comprehensive error handling for all scenarios
- **CSRF Protection**: Forms are protected against CSRF attacks

## Email Configuration

The system uses the existing SMTP configuration from:
- `proctor/core/config/SMTP_credentials.json`

Make sure this file contains valid SMTP credentials:
```json
{
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": 465,
    "SMTP_USER": "your-email@gmail.com",
    "SMTP_API_KEY": "your-app-password",
    "FROM_EMAIL": "your-email@gmail.com"
}
```

## Error Handling

The system handles various error scenarios:

1. **Invalid Email**: Shows "No user found with this email address"
2. **Email Send Failure**: Shows "Failed to send email. Please try again"
3. **Database Errors**: Shows specific error messages
4. **Missing Email**: Shows "Please enter your email address"

## User Experience

### Before Reset
- User forgets password
- Cannot access the system
- Needs to contact administrator

### After Reset
- User clicks "Forgot password?"
- Enters email address
- Receives new password via email
- Can immediately login with existing ID and new password

## Benefits

1. **User Convenience**: Users can reset passwords without admin intervention
2. **ID Consistency**: Users keep their familiar IDs
3. **Security**: Secure password generation and email delivery
4. **Self-Service**: Reduces administrative overhead
5. **Immediate Access**: Users can login immediately after reset

## Future Enhancements

- Add password strength requirements
- Implement password expiration
- Add rate limiting for reset attempts
- Create password change functionality after login
- Add audit logging for password resets 