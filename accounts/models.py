# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        COMPETITOR = 'competitor', 'Competitor'
        JUDGE = 'judge', 'Judge'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=20, choices=Role.choices, blank=True, null=True)
    university = models.CharField(max_length=150, blank=True)
    student_id = models.CharField(max_length=50, blank=True)
    is_rwandan_citizen = models.BooleanField(default=False)

    def __str__(self):
        return self.username