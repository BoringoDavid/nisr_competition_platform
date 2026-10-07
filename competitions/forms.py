from django import forms
from .models import Team
from .models import Competition


# this is for team creation form
class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'competition']


#========== form for inviting team member ==============
from django.contrib.auth import get_user_model

User = get_user_model()


class InviteMemberForm(forms.Form):
    email = forms.EmailField()




class CompetitionForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = ['name', 'track', 'description', 'registration_deadline', 'submission_deadline', 'status']
        widgets = {
            'registration_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'submission_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }