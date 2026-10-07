from django.db import models
from django.conf import settings

class Competition(models.Model):
    class Track(models.TextChoices):
        INFOGRAPHICS = 'infographics', 'Infographics'
        HACKATHON = 'hackathon', 'Hackathon'
        HIGH_SCHOOL = 'high_school', 'High School'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        JUDGING = 'judging', 'Judging'
        CLOSED = 'closed', 'Closed'

    name = models.CharField(max_length=200)
    track = models.CharField(max_length=20, choices=Track.choices)
    description = models.TextField(blank=True)
    registration_deadline = models.DateTimeField()
    submission_deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_track_display()})"



class Team(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'

    name = models.CharField(max_length=150)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='teams')
    leader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='led_teams')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='teams', blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.competition.name}"

    def is_eligible(self):
        return self.members.filter(is_rwandan_citizen=True).exists()