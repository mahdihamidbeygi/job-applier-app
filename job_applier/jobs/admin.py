from django.contrib import admin
from .models import Job, JobSearch


@admin.register(JobSearch)
class JobSearchAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'location', 'is_active', 'last_run', 'created_at')
    list_filter = ('is_active', 'created_at', 'last_run')
    search_fields = ('user__email', 'title', 'location')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('user', 'title', 'location', 'is_active')}),
        ('Search Criteria', {
            'fields': (
                'keywords',
                'excluded_keywords',
                'job_types',
                'experience_level',
                'salary_range'
            )
        }),
        ('Notifications', {'fields': ('notification_preferences', 'last_run')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type', 'is_expired', 'is_applied', 'posted_date')
    list_filter = ('job_type', 'is_expired', 'is_applied', 'posted_date', 'source')
    search_fields = ('title', 'company', 'location')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-posted_date',)

    fieldsets = (
        (None, {
            'fields': (
                'search',
                'title',
                'company',
                'location',
                'description',
                'requirements'
            )
        }),
        ('Job Details', {
            'fields': (
                'salary_range',
                'job_type',
                'experience_level',
                'url',
                'source',
                'posted_date',
                'expires_at',
                'is_expired',
                'is_applied',
                'application_url'
            )
        }),
        ('Company Info', {'fields': ('company_logo', 'company_description', 'benefits')}),
        ('Additional Info', {'fields': ('remote_work', 'visa_sponsorship', 'match_score', 'match_details')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
