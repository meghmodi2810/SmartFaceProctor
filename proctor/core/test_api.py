"""
Test script to verify API endpoints return JSON
Run this from Django shell: python manage.py shell < test_api.py
"""
import requests

# Test the semester API endpoint
url = "http://127.0.0.1:8000/student/api/semesters/1/"
print(f"Testing: {url}")
print("="*50)

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"First 500 chars of response:")
    print(response.text[:500])
    print("="*50)
    
    # Try to parse as JSON
    try:
        json_data = response.json()
        print("JSON parsed successfully:")
        print(json_data)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        
except Exception as e:
    print(f"Request failed: {e}")
