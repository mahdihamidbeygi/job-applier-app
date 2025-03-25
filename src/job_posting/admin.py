from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'job_type', 'experience_level', 'created_at', 'is_active']
    list_filter = ['job_type', 'experience_level', 'is_active', 'created_at']
    search_fields = ['title', 'company', 'location', 'description', 'requirements']
    prepopulated_fields = {'slug': ('title', 'company')}
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
