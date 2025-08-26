from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse
from .models import User, BugReport
import os
from django.conf import settings

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_active')
    change_list_template = "admin/core/user_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-sheet-emails/', self.admin_site.admin_view(self.send_sheet_emails), name='send-sheet-emails'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        send_url = reverse('admin:send-sheet-emails')
        extra_context['send_sheet_emails_url'] = send_url
        return super().changelist_view(request, extra_context=extra_context)

    def send_sheet_emails(self, request):
        from core.Modules.send_email_using_sheets import SmartFaceProctorMailer
        import os
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        smtp_credentials_path = os.path.join(BASE_DIR, 'config', 'SMTP_credentials.json')
        google_credentials_path = os.path.join(BASE_DIR, 'config', 'credentials.json')
        # TODO: You may want to make the sheet URL configurable or store it in settings
        sheet_url = "https://docs.google.com/spreadsheets/d/1682Pl8z4Ix4IxI7UGfbZgcX6p_gzMpRl2tRi0_my9kI/edit?gid=0#gid=0"
        sheet_name = 'Sheet1'
        password_length = 12
        mailer = SmartFaceProctorMailer(
            smtp_credentials_path=smtp_credentials_path,
            google_credentials_path=google_credentials_path,
            sheet_url=sheet_url,
            sheet_name=sheet_name,
            password_length=password_length
        )
        email_subject = "Your Smart Face Proctor System Login"
        email_body_template = (
            "Hello {user_type},\n\n"
            "Your ID is: {user_id}\n"
            "Your password is: {password}\n\n"
            "Best Regards,\nSmart Face Proctor System"
        )
        try:
            mailer.process_and_send(email_subject, email_body_template)
            self.message_user(request, "Emails sent successfully to all users in the sheet.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error sending emails: {e}", level=messages.ERROR)
        return redirect('..')

admin.site.register(User, UserAdmin)

class BugReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'reporter', 'bug_type', 'priority', 'status', 'created_at')
    list_filter = ('bug_type', 'priority', 'status', 'created_at')
    search_fields = ('title', 'description', 'reporter__username')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('reporter')

admin.site.register(BugReport, BugReportAdmin)
