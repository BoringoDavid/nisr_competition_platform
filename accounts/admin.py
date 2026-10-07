from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'university', 'student_id', 'is_rwandan_citizen')}),
    )
    list_display = ('username', 'email', 'role', 'is_superuser', 'is_staff')
    list_filter = ('role', 'is_superuser', 'is_staff')