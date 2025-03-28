from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    UserProfile, WorkExperience, Project, Education,
    Certification, Publication, Skill
)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_select_related = ('userprofile',)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ('position', 'company', 'profile', 'start_date', 'end_date')
    list_filter = ('profile', 'company')
    search_fields = ('position', 'company', 'description')
    ordering = ('-start_date',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'profile', 'start_date', 'end_date')
    list_filter = ('profile',)
    search_fields = ('title', 'description')
    ordering = ('-start_date',)

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('degree', 'institution', 'profile', 'start_date', 'end_date')
    list_filter = ('profile', 'institution')
    search_fields = ('degree', 'institution', 'description')
    ordering = ('-start_date',)

@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'issuer', 'profile', 'issue_date', 'expiry_date')
    list_filter = ('profile', 'issuer')
    search_fields = ('name', 'issuer')
    ordering = ('-issue_date',)

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'authors', 'profile', 'publication_date')
    list_filter = ('profile',)
    search_fields = ('title', 'authors')
    ordering = ('-publication_date',)

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'proficiency', 'profile')
    list_filter = ('profile', 'category', 'proficiency')
    search_fields = ('name',)
    ordering = ('name',)
