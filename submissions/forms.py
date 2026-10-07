from django import forms
from .models import Submission


class HackathonSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['github_link', 'deployed_link', 'documentation', 'agree_ip', 'disclose_ai']

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('github_link') and not cleaned.get('deployed_link'):
            raise forms.ValidationError("Provide at least GitHub or deployed link.")
        if not cleaned.get('agree_ip'):
            raise forms.ValidationError("You must agree to IP terms.")
        return cleaned


class InfographicsSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['static_file', 'dynamic_file', 'dynamic_link', 'agree_ip', 'disclose_ai']

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('static_file'):
            raise forms.ValidationError("Static file is required.")
        if not cleaned.get('dynamic_file') and not cleaned.get('dynamic_link'):
            raise forms.ValidationError("Provide dynamic file or link.")
        if not cleaned.get('agree_ip'):
            raise forms.ValidationError("You must agree to IP terms.")
        return cleaned