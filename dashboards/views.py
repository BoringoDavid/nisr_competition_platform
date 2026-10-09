from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from competitions.models import Team, Competition
from submissions.models import Submission

User = get_user_model()

@login_required
def competitor_dashboard(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    teams = Team.objects.filter(members=request.user)
    submissions = Submission.objects.filter(team__in=teams)
    open_competitions = Competition.objects.filter(status=Competition.Status.OPEN)
    return render(request, 'dashboards/competitor.html', {
        'teams': teams,
        'submissions': submissions,
        'open_competitions': open_competitions,
    })


@login_required
def judge_dashboard(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    return render(request, 'dashboards/judge.html')


@login_required
def admin_dashboard(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    if request.user.role != User.Role.ADMIN:
        return redirect('competitor_dashboard')
    return render(request, 'dashboards/admin.html', {
        'total_competitors': User.objects.filter(role=User.Role.COMPETITOR).count(),
        'total_judges': User.objects.filter(role=User.Role.JUDGE).count(),
        'total_teams': Team.objects.count(),
        'total_submissions': Submission.objects.count(),
        'users': User.objects.all().order_by('-date_joined'),
        'teams': Team.objects.all().order_by('-created_at'),
        'submissions': Submission.objects.all().order_by('-submitted_at'),
        'competitions': Competition.objects.all().order_by('-created_at'),
    })