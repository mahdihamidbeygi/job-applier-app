from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type', 'experience_level', 'posted_by', 'created_at', 'is_active')
    list_filter = ('job_type', 'experience_level', 'is_active', 'created_at')
    search_fields = ('title', 'company', 'description', 'requirements')
    readonly_fields = ('created_at', 'updated_at', 'slug')
    fieldsets = (
        (None, {
            'fields': ('title', 'company', 'location', 'description', 'requirements')
        }),
        ('Job Details', {
            'fields': ('salary_range', 'job_type', 'experience_level', 'deadline')
        }),
        ('Metadata', {
            'fields': ('posted_by', 'created_at', 'updated_at', 'slug', 'is_active'),
            'classes': ('collapse',)
        }),
    )
