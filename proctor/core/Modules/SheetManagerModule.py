import gspread
from google.oauth2.service_account import Credentials
from urllib.parse import urlparse
import re
import os
from django.conf import settings

def extract_sheet_id(sheet_url):
    """Extract the sheet ID from a Google Sheets URL."""
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
    if match:
        return match.group(1)
    raise ValueError('Invalid Google Sheet URL')


def get_questions_from_sheet(sheet_url, credentials_path='config/credentials.json', worksheet_index=0):
    # Make the path absolute relative to the Django BASE_DIR
    abs_credentials_path = os.path.join(settings.BASE_DIR, 'core', credentials_path)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(abs_credentials_path, scopes=scopes)
    client = gspread.authorize(creds)
    sheet_id = extract_sheet_id(sheet_url)
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet(worksheet_index)
    all_data = worksheet.get_all_values()
    if not all_data:
        return []
    headers = all_data[0]
    questions = [dict(zip(headers, row)) for row in all_data[1:]]
    return questions

# if __name__ == "__main__":
#     #extract_sheet_id('https://docs.google.com/spreadsheets/d/1USlaahbuzmbDO9FKAdRHC-TJ7Ll1YH3i2gv0C0gznG8/edit?gid=0#gid=0')
#     questions = get_questions_from_sheet('https://docs.google.com/spreadsheets/d/1USlaahbuzmbDO9FKAdRHC-TJ7Ll1YH3i2gv0C0gznG8/edit?gid=0#gid=0')
#     print(questions)