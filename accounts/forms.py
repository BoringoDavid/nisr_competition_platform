from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class CompetitorSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'university', 'student_id', 'is_rwandan_citizen', 'password1', 'password2']


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'university', 'student_id', 'is_rwandan_citizen']
        widgets = {
            'is_rwandan_citizen': forms.CheckboxInput(),
        }


class CustomAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                "Your account has been deactivated. Please contact the administration for support.",
                code='inactive',
            )
        super().confirm_login_allowed(user)