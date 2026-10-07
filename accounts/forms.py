from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class CompetitorSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'university', 'student_id', 'is_rwandan_citizen', 'password1', 'password2']