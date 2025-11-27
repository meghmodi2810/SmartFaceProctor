import os
import json

# Detect if running on Render
RUNNING_ON_RENDER = os.environ.get("RENDER", "").lower() == "true"

def get_smtp_credentials():
    """
    Load SMTP credentials from environment variable path (Render) or local JSON file
    """
    if RUNNING_ON_RENDER:
        # On Render, get path from environment variable
        smtp_cred_path = os.environ.get("SMTP_CRED", "/etc/secrets/SMTP_credentials.json")
        with open(smtp_cred_path, 'r') as f:
            return json.load(f)
    else:
        # Local development - load from local JSON file
        cred_path = os.path.join(
            os.path.dirname(__file__),
            "SMTP_credentials.json"
        )
        with open(cred_path, 'r') as f:
            return json.load(f)

def get_smtp_credentials_path():
    """
    Get the path to SMTP credentials file
    """
    if RUNNING_ON_RENDER:
        return os.environ.get("SMTP_CRED", "/etc/secrets/SMTP_credentials.json")
    else:
        return os.path.join(
            os.path.dirname(__file__),
            "SMTP_credentials.json"
        )

def get_google_credentials_path():
    """
    Get the path to Google Sheets credentials file
    """
    if RUNNING_ON_RENDER:
        return os.environ.get("GOOGLE_SHEETS_CRED", "/etc/secrets/credentials.json")
    else:
        return os.path.join(
            os.path.dirname(__file__),
            "credentials.json"
        )

# Convenience exports
smtp_credentials = get_smtp_credentials()
smtp_credentials_path = get_smtp_credentials_path()
google_credentials_path = get_google_credentials_path()
