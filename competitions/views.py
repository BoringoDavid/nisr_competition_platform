from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import TeamForm
from django.contrib import messages
from .forms import TeamForm, InviteMemberForm
from .models import Team

@login_required
def create_team(request):
    form = TeamForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        team = form.save(commit=False)
        team.leader = request.user
        team.save()
        team.members.add(request.user)
        return redirect('my_team')
    return render(request, 'competitions/create_team.html', {'form': form})


@login_required
def my_team(request):
    teams = request.user.teams.all()
    return render(request, 'competitions/my_team.html', {'teams': teams})

# for inviting team member to join the team
@login_required
def invite_member(request, team_id):
    team = Team.objects.get(id=team_id, leader=request.user)
    form = InviteMemberForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return render(request, 'competitions/invite_member.html', {'form': form, 'team': team})

        if team.members.count() >= 2:
            messages.error(request, "Team is full (max 2 members).")
        elif team.members.filter(id=user.id).exists():
            messages.error(request, "User already in team.")
        else:
            team.members.add(user)
            messages.success(request, f"{user.username} added.")

    return render(request, 'competitions/invite_member.html', {'form': form, 'team': team})