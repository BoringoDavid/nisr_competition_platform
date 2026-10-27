from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse
from .forms import CompetitionForm
from .models import Invitation, Team

User = get_user_model()


# @login_required
# def create_competition(request):
#     if request.user.is_superuser:
#         return redirect('/admin/')
#     if request.user.role != User.Role.ADMIN:
#         return redirect('competitor_dashboard')

#     form = CompetitionForm(request.POST or None)
#     if request.method == 'POST' and form.is_valid():
#         form.save()
#         messages.success(request, "Competition created.")
#         return redirect('admin_dashboard')

#     return render(request, 'competitions/create_competition.html', {
#         'form': form, 'active': 'competitions',
#     })

@login_required
def create_competition(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    if request.user.role != User.Role.ADMIN:
        return redirect('competitor_dashboard')

    form = CompetitionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Competition created.")
        return redirect('admin_competitions')   # ← changed

    return render(request, 'competitions/create_competition.html', {
        'form': form, 'active': 'competitions',
    })


def accept_invitation(request, token):
    if not request.user.is_authenticated:
        invite = get_object_or_404(Invitation, token=token)
        return redirect(f"{reverse('signup')}?email={invite.email}&next={request.path}")

    invite = get_object_or_404(Invitation, token=token)

    if invite.status != Invitation.Status.PENDING:
        messages.error(request, "Invitation no longer valid.")
        return redirect('competitor_dashboard')

    if invite.is_expired():
        invite.status = Invitation.Status.EXPIRED
        invite.save()
        messages.error(request, "Invitation expired.")
        return redirect('competitor_dashboard')

    if request.user.email != invite.email:
        messages.error(request, "This invitation was sent to a different email.")
        return redirect('competitor_dashboard')

    team = invite.team
    if team.is_full():
        messages.error(request, "Team is full.")
    else:
        team.members.add(request.user)
        team.update_status()
        invite.status = Invitation.Status.ACCEPTED
        invite.save()
        messages.success(request, f"You joined {team.name}!")

    return redirect('my_team')