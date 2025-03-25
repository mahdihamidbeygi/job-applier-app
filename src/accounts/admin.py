from django.contrib import admin
from src.accounts.models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'is_employer', 'created_at', 'updated_at')
    list_filter = ('is_employer', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'location')
    raw_id_fields = ('user',)
