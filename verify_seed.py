import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nisr_platform.settings")
django.setup()
from accounts.models import User
from competitions.models import Competition
from evaluations.models import Assignment, Evaluation
c = Competition.objects.get(name="NISR Data Viz Challenge 2026")
print("status       :", c.status)
print("criteria     :", list(c.criteria.values_list("name", "weight")))
print("weight sum   :", sum(cr.weight for cr in c.criteria.all()))
print("assignments  :", Assignment.objects.filter(submission__competition=c).count())
print("evaluations  :", Evaluation.objects.count())
for e in Evaluation.objects.all():
    print("  done eval total:", e.total, "/100  by", e.assignment.judge.username)
print("users        :", ", ".join(u.username + "(" + u.role + ")" for u in User.objects.all()))
