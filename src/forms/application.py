from django import forms
from ..models.application import Application

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cover_letter', 'resume', 'notes']
        widgets = {
            'cover_letter': forms.Textarea(attrs={'rows': 10}),
            'notes': forms.Textarea(attrs={'rows': 5}),
        }

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            if resume.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError('Resume file size must not exceed 5MB.')
            if not resume.content_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                raise forms.ValidationError('Resume must be a PDF or Word document.')
        return resume
