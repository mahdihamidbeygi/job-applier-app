from django.contrib import admin
from .models import TimeStampedModel, SoftDeleteModel

# Register your models here.

@admin.register(TimeStampedModel)
class TimeStampedModelAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(SoftDeleteModel)
class SoftDeleteModelAdmin(admin.ModelAdmin):
    list_display = ('is_deleted', 'deleted_at')
    list_filter = ('is_deleted',)
    search_fields = ('is_deleted',)
