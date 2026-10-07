from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from competitions.models import Team
from .models import Submission
from .forms import HackathonSubmissionForm, InfographicsSubmissionForm


@login_required
def submit(request, team_id):
    team = get_object_or_404(Team, id=team_id, leader=request.user)
    comp = team.competition

    if timezone.now() > comp.submission_deadline:
        messages.error(request, "Submission deadline passed.")
        return redirect('my_team')

    if comp.track == 'hackathon':
        FormClass = HackathonSubmissionForm
    elif comp.track == 'infographics':
        FormClass = InfographicsSubmissionForm
    else:
        messages.error(request, "Track not supported yet.")
        return redirect('my_team')

    instance = getattr(team, 'submission', None)
    form = FormClass(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        sub = form.save(commit=False)
        sub.team = team
        sub.competition = comp
        sub.is_late = timezone.now() > comp.submission_deadline
        sub.save()
        messages.success(request, "Submission saved.")
        return redirect('my_team')

    return render(request, 'submissions/submit.html', {'form': form, 'team': team})
