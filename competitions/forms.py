from django import forms
from .models import Team

# this is for team creation form
class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'competition']


#========== form for inviting team member ==============
from django.contrib.auth import get_user_model

User = get_user_model()


class InviteMemberForm(forms.Form):
    username = forms.CharField(max_length=150)