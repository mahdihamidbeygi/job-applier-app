from django import forms
from django.core.validators import RegexValidator, URLValidator
from django.utils import timezone

from .models import (
    Certification,
    Education,
    JobListing,
    JobPlatformPreference,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'name', 'title', 'phone', 'email', 'location',
            'bio', 'github_url', 'linkedin_url', 'address', 'city', 
            'state', 'country', 'postal_code', 'website', 'linkedin', 'github', 
            'headline', 'professional_summary', 'current_position', 'company', 
            'resume'
        ]
        widgets = {
            'professional_summary': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone_validator = RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'"
            )
            try:
                phone_validator(phone)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid phone number")
        return phone

    def clean_website(self):
        website = self.cleaned_data.get('website')
        if website:
            try:
                URLValidator()(website)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid URL")
        return website

    def clean_linkedin(self):
        linkedin = self.cleaned_data.get('linkedin')
        if linkedin:
            if not linkedin.startswith(('http://', 'https://')):
                linkedin = 'https://' + linkedin
            try:
                URLValidator()(linkedin)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid LinkedIn URL")
        return linkedin

    def clean_github(self):
        github = self.cleaned_data.get('github')
        if github:
            if not github.startswith(('http://', 'https://')):
                github = 'https://' + github
            try:
                URLValidator()(github)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid GitHub URL")
        return github

class WorkExperienceForm(forms.ModelForm):
    class Meta:
        model = WorkExperience
        fields = [
            'company', 'position', 'location', 'start_date', 'end_date',
            'current', 'description', 'achievements', 'technologies'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3, 'required': True}),
            'achievements': forms.Textarea(attrs={'rows': 3}),
            'technologies': forms.Textarea(attrs={'rows': 2}),
            'company': forms.TextInput(attrs={'required': True}),
            'position': forms.TextInput(attrs={'required': True}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        current = cleaned_data.get('current')

        if not current and not end_date:
            raise forms.ValidationError("Please provide an end date or mark as current position")

        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be earlier than start date")

        if current and end_date:
            raise forms.ValidationError("Cannot have both current position and end date")

        return cleaned_data

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'title', 'description', 'technologies', 'start_date', 'end_date',
            'github_url', 'live_url'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'technologies': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be earlier than start date")

        return cleaned_data

    def clean_github_url(self):
        github_url = self.cleaned_data.get('github_url')
        if github_url:
            if not github_url.startswith(('http://', 'https://')):
                github_url = 'https://' + github_url
            try:
                URLValidator()(github_url)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid GitHub URL")
        return github_url

    def clean_live_url(self):
        live_url = self.cleaned_data.get('live_url')
        if live_url:
            if not live_url.startswith(('http://', 'https://')):
                live_url = 'https://' + live_url
            try:
                URLValidator()(live_url)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid URL")
        return live_url

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = [
            'institution', 'degree', 'field_of_study', 'start_date', 'end_date',
            'current', 'gpa', 'achievements'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'achievements': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        current = cleaned_data.get('current')

        if not current and not end_date:
            raise forms.ValidationError("Please provide an end date or mark as current education")

        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be earlier than start date")

        if current and end_date:
            raise forms.ValidationError("Cannot have both current education and end date")

        return cleaned_data

    def clean_gpa(self):
        gpa = self.cleaned_data.get('gpa')
        if gpa is not None and (gpa < 0 or gpa > 4.0):
            raise forms.ValidationError("GPA must be between 0 and 4.0")
        return gpa

class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        fields = [
            'name', 'issuer', 'issue_date', 'expiry_date',
            'credential_id', 'credential_url'
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get('issue_date')
        expiry_date = cleaned_data.get('expiry_date')

        if expiry_date and issue_date and expiry_date < issue_date:
            raise forms.ValidationError("Expiry date cannot be earlier than issue date")

        return cleaned_data

    def clean_credential_url(self):
        credential_url = self.cleaned_data.get('credential_url')
        if credential_url:
            if not credential_url.startswith(('http://', 'https://')):
                credential_url = 'https://' + credential_url
            try:
                URLValidator()(credential_url)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid URL")
        return credential_url

class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = [
            'title', 'authors', 'publication_date', 'publisher',
            'journal', 'doi', 'abstract', 'url'
        ]
        widgets = {
            'publication_date': forms.DateInput(attrs={'type': 'date'}),
            'abstract': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_publication_date(self):
        publication_date = self.cleaned_data.get('publication_date')
        if publication_date and publication_date > timezone.now().date():
            raise forms.ValidationError("Publication date cannot be in the future")
        return publication_date

    def clean_url(self):
        url = self.cleaned_data.get('url')
        if url:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            try:
                URLValidator()(url)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid URL")
        return url

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'category', 'proficiency']

class JobPlatformPreferenceForm(forms.ModelForm):
    """Form for users to select their preferred job platforms"""
    preferred_platforms = forms.MultipleChoiceField(
        choices=JobListing.JOB_SOURCES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select the job platforms you want to search on"
    )

    class Meta:
        model = JobPlatformPreference
        fields = ['preferred_platforms'] 