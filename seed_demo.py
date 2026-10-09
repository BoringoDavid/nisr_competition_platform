"""One-off demo data for the evaluations (judging) app.

Run with SQLite so it works without MySQL:
    set DB_ENGINE=sqlite
    python manage.py migrate
    python seed_demo.py
    python manage.py runserver
"""
import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nisr_platform.settings")
django.setup()

from accounts.models import User
from competitions.models import Competition, Team
from submissions.models import Submission
from evaluations.models import (
    Criterion, Assignment, Evaluation, Score, JudgingRound,
)

PW = "Nisr!Demo2026"

admin, _ = User.objects.get_or_create(
    username="admin", defaults=dict(role=User.Role.ADMIN))
admin.role, admin.is_staff, admin.is_superuser = User.Role.ADMIN, True, True
admin.email = "admin@nisr.gov.rw"
admin.set_password(PW)
admin.save()

def mk_judge(username, first, last):
    u, _ = User.objects.get_or_create(
        username=username, defaults=dict(role=User.Role.JUDGE))
    u.role = User.Role.JUDGE
    u.first_name, u.last_name = first, last
    u.email = f"{username}@nisr.gov.rw"
    u.set_password(PW)
    u.save()
    return u

judge1 = mk_judge("judge1", "Alice", "Uwase")
judge2 = mk_judge("judge2", "Eric", "Mugisha")

def mk_comp(username, first, last, uni):
    u, _ = User.objects.get_or_create(
        username=username, defaults=dict(role=User.Role.COMPETITOR))
    u.role = User.Role.COMPETITOR
    u.first_name, u.last_name = first, last
    u.university = uni
    u.student_id = username.upper() + "001"
    u.is_rwandan_citizen = True
    u.set_password(PW)
    u.save()
    return u

c1 = mk_comp("claude", "Claude", "N.", "UR")
c2 = mk_comp("diane", "Diane", "M.", "UR")
c3 = mk_comp("patrick", "Patrick", "K.", "INES")
c4 = mk_comp("sandrine", "Sandrine", "A.", "ULK")

comp, _ = Competition.objects.get_or_create(
    name="NISR Data Viz Challenge 2026",
    defaults=dict(
        track=Competition.Track.INFOGRAPHICS,
        description="Turn national statistics into a clear, compelling infographic.",
        registration_deadline=timezone.now() - timedelta(days=30),
        submission_deadline=timezone.now() - timedelta(days=2),
        status=Competition.Status.JUDGING))
comp.status = Competition.Status.JUDGING
comp.save()

rubric = [
    ("Impact", "Does it change how the audience understands the data?", 40),
    ("Design", "Clarity, layout, colour, readability on mobile.", 25),
    ("Originality", "Fresh angle, creative use of the data.", 20),
    ("Presentation", "Titles, labels, sourcing, polish.", 15),
]
Criterion.objects.filter(competition=comp).delete()
for i, (name, desc, weight) in enumerate(rubric):
    Criterion.objects.create(
        competition=comp, name=name, description=desc,
        max_score=10, weight=weight, order=i)
criteria = list(Criterion.objects.filter(competition=comp).order_by("order"))

rnd, _ = JudgingRound.objects.get_or_create(
    competition=comp, order=1,
    defaults=dict(name="Round 1", cutoff_top_n=2,
                  status=JudgingRound.Status.ACTIVE))
rnd.name, rnd.cutoff_top_n, rnd.status = "Round 1", 2, JudgingRound.Status.ACTIVE
rnd.save()

def mk_team_sub(name, members, github, deployed):
    team, _ = Team.objects.get_or_create(
        name=name, competition=comp,
        defaults=dict(leader=members[0], status=Team.Status.CONFIRMED))
    team.leader = members[0]
    team.status = Team.Status.CONFIRMED
    team.save()
    team.members.set(members)
    sub, _ = Submission.objects.get_or_create(
        team=team, defaults=dict(competition=comp))
    sub.competition = comp
    sub.dynamic_link = deployed
    sub.github_link = github
    sub.agree_ip = True
    sub.save()
    return sub

s1 = mk_team_sub("Team Kigali", [c1, c2],
                 "https://github.com/demo/kigali", "https://demo.example/kigali")
s2 = mk_team_sub("Team Huye", [c3],
                 "https://github.com/demo/huye", "https://demo.example/huye")
s3 = mk_team_sub("Team Musanze", [c4],
                 "https://github.com/demo/musanze", "https://demo.example/musanze")
subs = [s1, s2, s3]

Assignment.objects.filter(submission__in=subs).delete()
for sub in subs:
    for j in (judge1, judge2):
        Assignment.objects.create(
            submission=sub, judge=j, judging_round=rnd,
            status=Assignment.Status.ASSIGNED)

asg = Assignment.objects.get(submission=s1, judge=judge1)
ev, _ = Evaluation.objects.get_or_create(
    assignment=asg,
    defaults=dict(comments="Strong narrative and excellent mobile readability."))
ev.comments = "Strong narrative and excellent mobile readability."
ev.save()
Score.objects.filter(evaluation=ev).delete()
marks = {
    "Impact": (8, "Clear policy takeaway; good hook for non-technical readers."),
    "Design": (6, "Clean layout, but the mobile legend overlaps on small screens."),
    "Originality": (7, "Nice comparison angle using two census years."),
    "Presentation": (9, "Polished titles, labels, and sources cited properly."),
}
for crit in criteria:
    value, why = marks.get(crit.name, (5, ""))
    Score.objects.create(
        evaluation=ev, criterion=crit, value=value, comment=why)
ev.recompute_total(save=True)
asg.status = Assignment.Status.DONE
asg.save()

print("Demo seed complete.")
print("  Competition:", comp.name, "->", comp.status)
print("  Teams:", ", ".join(t.name for t in comp.teams.all()))
print("  Assignments:", Assignment.objects.filter(submission__in=subs).count())
print("  judge1 done-eval total on Team Kigali:", ev.total, "/100")
print("  Logins -> admin / judge1 / judge2  (all password: %s)" % PW)

