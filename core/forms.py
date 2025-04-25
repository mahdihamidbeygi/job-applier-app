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


def clean_url_field(cleaned_data, field_name, prefix_https=True):
    """Generic URL field cleaner.

    Args:
        cleaned_data: The form's cleaned_data dictionary
        field_name: The name of the field to clean
        prefix_https: Whether to add https:// prefix if missing

    Returns:
        The cleaned URL value
    """
    url = cleaned_data.get(field_name, "")
    if url:
        if prefix_https and not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            URLValidator()(url)
        except forms.ValidationError:
            raise forms.ValidationError(f"Please enter a valid URL for {field_name}")
    return url


def validate_date_range(
    cleaned_data,
    start_date_field="start_date",
    end_date_field="end_date",
    current_field=None,
    entity_name="position",
):
    """Validate that start date comes before end date and handle 'current' checkbox logic.

    Args:
        cleaned_data: The form's cleaned_data dictionary
        start_date_field: The name of the start date field
        end_date_field: The name of the end date field
        current_field: The name of the current/ongoing field, if any
        entity_name: Name of the entity for error messages (e.g., "position", "education")

    Returns:
        The cleaned data dictionary
    """
    start_date = cleaned_data.get(start_date_field)
    end_date = cleaned_data.get(end_date_field)
    current = cleaned_data.get(current_field) if current_field else None

    if current_field and not current and not end_date:
        raise forms.ValidationError(f"Please provide an end date or mark as current {entity_name}")

    if end_date and start_date and end_date < start_date:
        raise forms.ValidationError("End date cannot be earlier than start date")

    if current_field and current and end_date:
        raise forms.ValidationError(f"Cannot have both current {entity_name} and end date")

    return cleaned_data


class UserProfileForm(forms.ModelForm):
    # Add a non-model field for email that updates user.email
    email = forms.EmailField(required=False)

    class Meta:
        model = UserProfile
        fields = [
            "name",
            "title",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "website",
            "github_url",
            "linkedin_url",
            "headline",
            "professional_summary",
            "current_position",
            "company",
            "resume",
        ]
        widgets = {
            "professional_summary": forms.Textarea(attrs={"rows": 4}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize the email field with the user's email
        if self.instance and self.instance.user:
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        # Save the user email
        if self.cleaned_data.get("email") and self.instance and self.instance.user:
            self.instance.user.email = self.cleaned_data.get("email")
            if commit:
                self.instance.user.save(update_fields=["email"])
        return super().save(commit)

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            phone_validator = RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Phone number must be entered in the format: '+999999999'",
            )
            try:
                phone_validator(phone)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid phone number")
        return phone

    def clean_website(self):
        return clean_url_field(self.cleaned_data, "website")

    def clean_linkedin_url(self):
        return clean_url_field(self.cleaned_data, "linkedin_url")

    def clean_github_url(self):
        return clean_url_field(self.cleaned_data, "github_url")


class WorkExperienceForm(forms.ModelForm):
    class Meta:
        model = WorkExperience
        fields = [
            "company",
            "position",
            "location",
            "start_date",
            "end_date",
            "current",
            "description",
            "achievements",
            "technologies",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3, "required": True}),
            "achievements": forms.Textarea(attrs={"rows": 3}),
            "technologies": forms.Textarea(attrs={"rows": 2}),
            "company": forms.TextInput(attrs={"required": True}),
            "position": forms.TextInput(attrs={"required": True}),
        }

    def clean(self):
        cleaned_data = super().clean()
        return validate_date_range(cleaned_data, current_field="current", entity_name="position")


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "technologies",
            "start_date",
            "end_date",
            "github_url",
            "live_url",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "technologies": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        return validate_date_range(cleaned_data)

    def clean_github_url(self):
        return clean_url_field(self.cleaned_data, "github_url")

    def clean_live_url(self):
        return clean_url_field(self.cleaned_data, "live_url")


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = [
            "institution",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "current",
            "gpa",
            "achievements",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "achievements": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        return validate_date_range(cleaned_data, current_field="current", entity_name="education")

    def clean_gpa(self):
        gpa = self.cleaned_data.get("gpa")
        if gpa is not None and (gpa < 0 or gpa > 4.0):
            raise forms.ValidationError("GPA must be between 0 and 4.0")
        return gpa


class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        fields = ["name", "issuer", "issue_date", "expiry_date", "credential_id", "credential_url"]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        return validate_date_range(
            cleaned_data, start_date_field="issue_date", end_date_field="expiry_date"
        )

    def clean_credential_url(self):
        return clean_url_field(self.cleaned_data, "credential_url")


class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = [
            "title",
            "authors",
            "publication_date",
            "publisher",
            "journal",
            "doi",
            "abstract",
            "url",
        ]
        widgets = {
            "publication_date": forms.DateInput(attrs={"type": "date"}),
            "abstract": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_publication_date(self):
        publication_date = self.cleaned_data.get("publication_date")
        if publication_date and publication_date > timezone.now().date():
            raise forms.ValidationError("Publication date cannot be in the future")
        return publication_date

    def clean_url(self):
        return clean_url_field(self.cleaned_data, "url")


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "category", "proficiency"]


class JobPlatformPreferenceForm(forms.ModelForm):
    """Form for users to select their preferred job platforms"""

    preferred_platforms = forms.MultipleChoiceField(
        choices=JobListing.JOB_SOURCES,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select your preferred job platforms",
    )

    class Meta:
        model = JobPlatformPreference
        fields = ["preferred_platforms"]
