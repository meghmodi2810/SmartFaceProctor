# AJAX Search and Bulk Import Implementation Guide

## Summary of Changes Implemented

### 1. ✅ Homepage Search for Exam Results
**File:** `proctor/core/templates/home.html`
- Added a search section with AJAX functionality
- Students can search for exam results by username or exam name
- Real-time search with debounce (500ms delay)
- Displays results with score, grade, and date information

### 2. ✅ Student Results Page - AJAX Search
**File:** `proctor/core/templates/student_results.html`
- Added search box at the top of the results page
- Students can filter their own exam results by exam title
- Real-time AJAX search with instant results
- Search updates the table without page reload

### 3. ✅ Admin Users Page - AJAX Search
**File:** `proctor/core/templates/admin_users.html`
- Added AJAX search for user management
- Combined search by username, email, or name
- Role filter integration with search
- Real-time updates without page refresh
- Modified import modal to accept file uploads instead of fixed Google Sheets

### 4. ✅ Admin Dashboard - Fixed Sidebar Issue
**File:** `proctor/core/templates/admin_dashboard.html`
- Fixed: Now properly extends `admin_base.html`
- Removed duplicate sidebar styles
- Sidebar now appears consistently across all admin pages

### 5. ✅ User Import Guide Created
**File:** `proctor/core/templates/admin_user_import_guide.html`
- Created comprehensive step-by-step guide similar to exam scheduling guide
- Shows template format with example data
- Explains required vs optional fields
- Includes troubleshooting section
- Download button for user template

### 6. ✅ API Endpoints Added
**File:** `proctor/core/views_api.py`
- `search_results()` - Homepage exam results search
- `search_student_results()` - Student's own results search
- `admin_search_users()` - Admin user search with filtering

### 7. ⚠️ Backend Functions to Complete

The following functions need to be added/updated in `proctor/core/admin_views.py`:

```python
@admin_required
def admin_import_users(request):
    """Import users from CSV or Excel file"""
    if request.method == 'POST':
        user_file = request.FILES.get('user_file')
        if user_file:
            try:
                import pandas as pd
                import io
                
                # Read file based on extension
                file_extension = user_file.name.split('.')[-1].lower()
                
                if file_extension == 'csv':
                    df = pd.read_csv(io.StringIO(user_file.read().decode('utf-8')))
                elif file_extension in ['xlsx', 'xls']:
                    df = pd.read_excel(user_file)
                else:
                    messages.error(request, 'Invalid file format. Please upload CSV or Excel file.')
                    return redirect('admin_users')
                
                # Validate required columns
                required_columns = ['username', 'email', 'password', 'role']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    messages.error(request, f'Missing required columns: {", ".join(missing_columns)}')
                    return redirect('admin_users')
                
                # Import users
                imported_count = 0
                skipped_count = 0
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Check if user already exists
                        if User.objects.filter(username=row['username']).exists():
                            skipped_count += 1
                            errors.append(f"Row {index + 2}: Username '{row['username']}' already exists")
                            continue
                        
                        if User.objects.filter(email=row['email']).exists():
                            skipped_count += 1
                            errors.append(f"Row {index + 2}: Email '{row['email']}' already exists")
                            continue
                        
                        # Validate role
                        if row['role'] not in ['Student', 'Faculty', 'Admin']:
                            skipped_count += 1
                            errors.append(f"Row {index + 2}: Invalid role '{row['role']}'")
                            continue
                        
                        # Create user
                        user = User.objects.create_user(
                            username=str(row['username']).strip(),
                            email=str(row['email']).strip(),
                            password=str(row['password']),
                            first_name=str(row.get('first_name', '')).strip() if pd.notna(row.get('first_name')) else '',
                            last_name=str(row.get('last_name', '')).strip() if pd.notna(row.get('last_name')) else '',
                            role=str(row['role']).strip(),
                            is_active=True
                        )
                        imported_count += 1
                        
                    except Exception as e:
                        skipped_count += 1
                        errors.append(f"Row {index + 2}: {str(e)}")
                
                # Show results
                if imported_count > 0:
                    messages.success(request, f'Successfully imported {imported_count} users.')
                
                if skipped_count > 0:
                    error_msg = f'Skipped {skipped_count} users. '
                    if len(errors) <= 10:
                        error_msg += 'Errors: ' + '; '.join(errors[:10])
                    else:
                        error_msg += f'First 10 errors: ' + '; '.join(errors[:10]) + f' (and {len(errors) - 10} more)'
                    messages.warning(request, error_msg)
                
            except Exception as e:
                messages.error(request, f'Error importing users: {str(e)}')
        else:
            messages.error(request, 'No file uploaded.')
    
    return redirect('admin_users')


@admin_required
def admin_user_import_guide(request):
    """Display the user import guide"""
    return render(request, 'admin_user_import_guide.html', {'admin': request.user})


@admin_required
def download_user_template(request):
    """Download user import template"""
    import openpyxl
    from django.http import HttpResponse
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Users"
    
    # Add headers
    headers = ['username', 'email', 'password', 'role', 'first_name', 'last_name']
    ws.append(headers)
    
    # Add sample data
    ws.append(['john_doe', 'john@example.com', 'Pass@1234', 'Student', 'John', 'Doe'])
    ws.append(['jane_smith', 'jane@example.com', 'Secure@5678', 'Faculty', 'Jane', 'Smith'])
    
    # Style headers
    from openpyxl.styles import Font, PatternFill
    header_fill = PatternFill(start_color="667EEA", end_color="667EEA", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    
    # Set column widths
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15
    
    # Save to response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=UsersTemplate.xlsx'
    wb.save(response)
    
    return response
```

### 8. ⚠️ URL Patterns to Add

Add these to `proctor/core/urls.py`:

```python
# API endpoints for AJAX search
path('api/search-results/', views_api.search_results, name='search_results'),
path('api/search-student-results/', views_api.search_student_results, name='search_student_results'),
path('api/admin/search-users/', views_api.admin_search_users, name='admin_search_users'),

# Admin user import guide and template
path('customadmin/users/import-guide/', admin_views.admin_user_import_guide, name='admin_user_import_guide'),
path('customadmin/users/download-template/', admin_views.download_user_template, name='download_user_template'),
```

### 9. ⚠️ Dependencies Required

Make sure these packages are installed:
```bash
pip install pandas openpyxl
```

Add to `requirements.txt`:
```
pandas>=1.5.0
openpyxl>=3.0.0
```

## What Each Feature Does

### Homepage Search
- **URL:** `http://127.0.0.1:8000/`
- **Functionality:** Public search for exam results (requires login)
- **Search By:** Student username or exam title
- **Display:** Shows exam title, student, score, grade, and date

### Student Results Search
- **URL:** `http://127.0.0.1:8000/student/results/`
- **Functionality:** Students can search their own exam results
- **Search By:** Exam title
- **Display:** Filters the student's exam history table in real-time

### Admin User Search
- **URL:** `http://127.0.0.1:8000/customadmin/users/`
- **Functionality:** Admin can search and filter users
- **Search By:** Username, email, first name, or last name
- **Filters:** Combined with role filter (Student/Faculty/Admin)
- **Display:** Updates user table instantly

### Bulk User Import
- **URL:** `http://127.0.0.1:8000/customadmin/users/`
- **Button:** "Import from File"
- **Accepts:** CSV or Excel files (.csv, .xlsx, .xls)
- **Template:** Download from "Import Guide" button
- **Process:** 
  1. Upload file with user data
  2. System validates all entries
  3. Creates valid users
  4. Reports success count and any errors
  5. Skips duplicates automatically

### User Import Guide
- **URL:** `http://127.0.0.1:8000/customadmin/users/import-guide/`
- **Content:** Step-by-step instructions
- **Template Download:** Provides Excel template with sample data
- **Format:** username, email, password, role, first_name, last_name

## System Workflow Summary

### Corrected Workflow (as per user request):
1. **Register & Setup** - Create account and complete face enrollment
2. **Start Exam** - Access your scheduled exam and begin
3. **Face Detection** - AI detects face and verifies identity
4. **Exam Starts** - Questions are displayed
5. **Exam Ends** - Student submits answers
6. **Result Declaration** - Results automatically calculated and displayed

## Testing Checklist

- [ ] Test homepage search with various queries
- [ ] Verify student results search filters correctly
- [ ] Test admin user search with different filters
- [ ] Upload CSV file with users
- [ ] Upload Excel file with users
- [ ] Test with duplicate usernames/emails
- [ ] Test with invalid roles
- [ ] Verify error messages are clear
- [ ] Check that imported users can log in
- [ ] Confirm admin dashboard sidebar works on all pages
- [ ] Test user import guide page loads correctly
- [ ] Download and verify user template file

## Important Notes

1. **Pandas Dependency:** The bulk import requires pandas. Install with: `pip install pandas openpyxl`
2. **File Size Limits:** Django default file upload limit is 2.5MB. For larger imports, adjust `FILE_UPLOAD_MAX_MEMORY_SIZE` in settings.py
3. **Performance:** For very large user imports (1000+), consider implementing a background task queue
4. **Security:** Imported passwords are hashed automatically by Django's `create_user()` method

## Files Modified/Created

### Modified:
1. `proctor/core/templates/home.html` - Added search section
2. `proctor/core/templates/student_results.html` - Added AJAX search
3. `proctor/core/templates/admin_users.html` - Added AJAX search and file upload
4. `proctor/core/templates/admin_dashboard.html` - Fixed to extend admin_base
5. `proctor/core/views_api.py` - Added API endpoints

### Created:
1. `proctor/core/templates/admin_user_import_guide.html` - User import guide

### To Update:
1. `proctor/core/admin_views.py` - Replace admin_import_users and add new functions
2. `proctor/core/urls.py` - Add API endpoints and new routes
3. `requirements.txt` - Add pandas and openpyxl

## Next Steps

1. Update `admin_views.py` with the new functions
2. Add URL patterns to `urls.py`
3. Install required packages: `pip install pandas openpyxl`
4. Test all search functionality
5. Test bulk user import with sample data
6. Verify admin dashboard sidebar consistency
