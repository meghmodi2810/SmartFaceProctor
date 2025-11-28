import os
import json

# Detect if running on Render
RUNNING_ON_RENDER = os.environ.get("RENDER", "").lower() == "true" or os.environ.get("ENV", "") == "render"

def get_smtp_credentials():
    """
    Load SMTP credentials from environment variable path (Render) or local JSON file
    Returns empty dict or environment variables if file doesn't exist (for build time)
    """
    if RUNNING_ON_RENDER:
        # On Render, get path from environment variable
        smtp_cred_path = os.environ.get("SMTP_CRED", "/etc/secrets/SMTP_credentials.json")
        
        # Check if file exists
        if not os.path.exists(smtp_cred_path):
            # Return environment variable based config (fallback during build)
            # Use SendGrid settings from environment
            return {
                'SMTP_HOST': os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net'),
                'SMTP_PORT': int(os.environ.get('EMAIL_PORT', 587)),
                'SMTP_USER': os.environ.get('EMAIL_HOST_USER', 'apikey'),
                'SMTP_API_KEY': os.environ.get('SENDGRID_API_KEY', os.environ.get('EMAIL_HOST_PASSWORD', '')),
                'FROM_EMAIL': os.environ.get('FROM_EMAIL', os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@smartfaceproctor.com')),
                'EMAIL_USE_TLS': os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true',
                'EMAIL_USE_SSL': os.environ.get('EMAIL_USE_SSL', 'False').lower() == 'true',
            }
        
        try:
            with open(smtp_cred_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load SMTP credentials from {smtp_cred_path}: {e}")
            return {}
    else:
        # Local development - load from local JSON file
        cred_path = os.path.join(
            os.path.dirname(__file__),
            "SMTP_credentials.json"
        )
        
        # Check if file exists locally
        if not os.path.exists(cred_path):
            print(f"Warning: SMTP credentials file not found at {cred_path}")
            return {}
        
        try:
            with open(cred_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load SMTP credentials: {e}")
            return {}

def get_smtp_credentials_path():
    """
    Get the path to SMTP credentials file
    Returns None if file doesn't exist
    """
    if RUNNING_ON_RENDER:
        path = os.environ.get("SMTP_CRED", "/etc/secrets/SMTP_credentials.json")
    else:
        path = os.path.join(
            os.path.dirname(__file__),
            "SMTP_credentials.json"
        )
    
    # Return path only if it exists
    return path if os.path.exists(path) else None

def get_google_credentials_path():
    """
    Get the path to Google Sheets credentials file
    Returns None if file doesn't exist
    """
    if RUNNING_ON_RENDER:
        path = os.environ.get("GOOGLE_SHEETS_CRED", "/etc/secrets/credentials.json")
    else:
        path = os.path.join(
            os.path.dirname(__file__),
            "credentials.json"
        )
    
    # Return path only if it exists
    return path if os.path.exists(path) else None

# Convenience exports - these won't fail during build
smtp_credentials = get_smtp_credentials()
smtp_credentials_path = get_smtp_credentials_path()
google_credentials_path = get_google_credentials_path()
