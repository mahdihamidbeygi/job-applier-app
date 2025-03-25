from django.contrib import admin
from .models import Application, ApplicationHistory


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'status', 'applied_date', 'created_at')
    list_filter = ('status', 'applied_date', 'created_at')
    search_fields = ('job__title', 'user__email', 'cover_letter')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-applied_date',)

    fieldsets = (
        (None, {'fields': ('job', 'user', 'status', 'applied_date')}),
        ('Application Details', {
            'fields': (
                'cover_letter',
                'resume',
                'notes',
                'follow_up_date',
                'interview_date',
                'interview_type',
                'interview_notes'
            )
        }),
        ('Response', {'fields': ('response_received', 'response_date', 'response_notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(ApplicationHistory)
class ApplicationHistoryAdmin(admin.ModelAdmin):
    list_display = ('application', 'status', 'changed_at', 'changed_by')
    list_filter = ('status', 'changed_at')
    search_fields = ('application__job__title', 'application__user__email', 'notes')
    readonly_fields = ('changed_at',)
    ordering = ('-changed_at',)

    fieldsets = (
        (None, {'fields': ('application', 'status', 'changed_by', 'changed_at')}),
        ('Notes', {'fields': ('notes',)}),
    )
