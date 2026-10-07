from django.db import models
from competitions.models import Team, Competition


class Submission(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='submission')
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)

    # Hackathon
    github_link = models.URLField(blank=True)
    deployed_link = models.URLField(blank=True)
    documentation = models.FileField(upload_to='docs/', blank=True)

    # Infographics
    static_file = models.FileField(upload_to='infographics/static/', blank=True)
    dynamic_file = models.FileField(upload_to='infographics/dynamic/', blank=True)
    dynamic_link = models.URLField(blank=True)

    # Common
    agree_ip = models.BooleanField(default=False)
    disclose_ai = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_late = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.team.name} — {self.competition.name}"
