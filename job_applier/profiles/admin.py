from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'location', 'is_public', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('user__email', 'full_name', 'location')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('user', 'full_name', 'bio', 'location')}),
        ('Professional Links', {'fields': ('linkedin_url', 'github_url', 'resume')}),
        ('Skills & Experience', {'fields': ('skills', 'experience', 'education')}),
        ('Preferences', {
            'fields': (
                'preferred_job_types',
                'preferred_locations',
                'preferred_industries',
                'salary_expectations',
                'availability'
            )
        }),
        ('Settings', {'fields': ('is_public', 'created_at', 'updated_at')}),
    )
