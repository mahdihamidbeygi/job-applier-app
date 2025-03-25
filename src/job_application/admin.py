from django.contrib import admin
from .models import Application

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['job', 'applicant', 'status', 'created_at', 'applied_date']
    list_filter = ['status', 'created_at', 'applied_date']
    search_fields = ['job__title', 'applicant__username', 'applicant__email', 'cover_letter', 'notes']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ['job', 'applicant']
