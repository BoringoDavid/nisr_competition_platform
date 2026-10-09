from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import TeamForm
from django.contrib import messages
from .forms import TeamForm, InviteMemberForm
from .models import Team
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .models import Invitation


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import CompetitionForm

User = get_user_model()


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
        return redirect('admin_dashboard')

    return render(request, 'competitions/create_competition.html', {'form': form})

    

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

#====================for inviting team member to join the team=========================
@login_required
def invite_member(request, team_id):
    team = get_object_or_404(Team, id=team_id, leader=request.user)
    form = InviteMemberForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']

        if team.is_full():
            messages.error(request, "Team is full (max 2 members).")
        elif team.members.filter(email=email).exists():
            messages.error(request, "User already in team.")
        elif Invitation.objects.filter(team=team, email=email, status=Invitation.Status.PENDING).exists():
            messages.error(request, "Invitation already sent to this email.")
        else:
            invite = Invitation.objects.create(team=team, email=email)
            link = request.build_absolute_uri(
                reverse('accept_invitation', args=[invite.token])
            )
            subject = f"You're invited to join team '{team.name}' on NISR Competition Platform"

            message = f"""Hello,

            You have been invited by {request.user.username} to join the team "{team.name}"
            for the competition: {team.competition.name} ({team.competition.get_track_display()}).

            Click the link below to accept the invitation:
            {link}

            This invitation expires on {invite.expires_at.strftime('%d %B %Y')}.

            If you were not expecting this invitation, you can ignore this email.

            — NISR Competition Platform
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            messages.success(request, f"Invitation sent to {email}.")

    invitations = team.invitations.filter(status=Invitation.Status.PENDING)
    return render(request, 'competitions/invite_member.html', {
        'form': form, 'team': team, 'invitations': invitations,
    })

#===================================== for accepting the invitation to join a team ===================================================
@login_required
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

