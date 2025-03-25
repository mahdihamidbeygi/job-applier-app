from django import forms
from .models import Application, Document

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cover_letter', 'resume', 'notes']
        widgets = {
            'cover_letter': forms.Textarea(attrs={'rows': 5}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['document_type', 'file', 'name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
