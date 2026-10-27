from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from django import forms

from competitions.models import Team, Competition, Invitation
from competitions.forms import TeamForm, InviteMemberForm
from submissions.models import Submission
from submissions.forms import HackathonSubmissionForm, InfographicsSubmissionForm
from public.models import ContactMessage

User = get_user_model()


# ==================== DASHBOARDS ====================

@login_required
def competitor_dashboard(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    teams = Team.objects.filter(members=request.user)
    submissions = Submission.objects.filter(team__in=teams)
    open_competitions = Competition.objects.filter(status=Competition.Status.OPEN)
    return render(request, 'dashboards/competitor_dashboard.html', {
        'teams': teams,
        'submissions': submissions,
        'open_competitions': open_competitions,
        'active': 'dashboard',
    })


@login_required
def judge_dashboard(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    return render(request, 'dashboards/judge_dashboard.html', {'active': 'dashboard'})


@login_required
def admin_dashboard(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    if request.user.role != User.Role.ADMIN:
        return redirect('competitor_dashboard')
    return render(request, 'dashboards/admin_dashboard.html', {
        'total_competitors': User.objects.filter(role=User.Role.COMPETITOR).count(),
        'total_judges': User.objects.filter(role=User.Role.JUDGE).count(),
        'total_teams': Team.objects.count(),
        'total_submissions': Submission.objects.count(),
        'users': User.objects.all().order_by('-date_joined'),
        'teams': Team.objects.all().order_by('-created_at'),
        'submissions': Submission.objects.all().order_by('-submitted_at'),
        'competitions': Competition.objects.all().order_by('-created_at'),
        'active': 'dashboard',
    })


# ==================== TEAM MANAGEMENT ====================

@login_required
def create_team(request):
    if request.user.role != User.Role.COMPETITOR:
        return redirect('competitor_dashboard')

    competition_id = request.GET.get('competition')
    initial = {}
    selected_competition = None

    if competition_id:
        try:
            selected_competition = Competition.objects.get(
                id=competition_id,
                status=Competition.Status.OPEN,
            )
            initial['competition'] = selected_competition
        except Competition.DoesNotExist:
            messages.error(request, "Competition not available.")
            return redirect('browse_competitions')

    form = TeamForm(request.POST or None, initial=initial)

    if competition_id:
        form.fields['competition'].widget = forms.HiddenInput()

    if request.method == 'POST' and form.is_valid():
        team = form.save(commit=False)
        team.leader = request.user
        team.save()
        team.members.add(request.user)
        messages.success(request, f"Team '{team.name}' created.")
        return redirect('my_team')

    return render(request, 'competitions/create_team.html', {
        'form': form,
        'active': 'teams',
        'selected_competition': selected_competition,
    })

@login_required
def my_team(request):
    teams = Team.objects.filter(members=request.user)
    return render(request, 'competitions/my_team.html', {
        'teams': teams, 'active': 'teams',
    })


@login_required
def team_detail(request, team_id):
    team = get_object_or_404(Team, id=team_id, members=request.user)
    return render(request, 'competitions/team_detail.html', {
        'team': team, 'active': 'teams',
    })


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
            body = f"""Hello,

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
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            messages.success(request, f"Invitation sent to {email}.")

    invitations = team.invitations.filter(status=Invitation.Status.PENDING)
    return render(request, 'competitions/invite_member.html', {
        'form': form, 'team': team, 'invitations': invitations,
        'active': 'teams',
    })


# ==================== SUBMISSIONS ====================

@login_required
def submit(request, team_id):
    from django.utils import timezone
    team = get_object_or_404(Team, id=team_id, leader=request.user)
    comp = team.competition

    if timezone.now() > comp.submission_deadline:
        messages.error(request, "Submission deadline has passed.")
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
        return redirect('my_submissions')

    return render(request, 'submissions/submit.html', {
        'form': form, 'team': team, 'active': 'submissions',
    })


@login_required
def my_submissions(request):
    teams = Team.objects.filter(members=request.user)
    submissions = Submission.objects.filter(team__in=teams)
    return render(request, 'submissions/my_submissions.html', {
        'submissions': submissions, 'active': 'submissions',
    })


# ==================== COMPETITIONS ====================

@login_required
def browse_competitions(request):
    competitions = Competition.objects.filter(status=Competition.Status.OPEN)
    return render(request, 'competitions/browse.html', {
        'competitions': competitions, 'active': 'competitions',
    })


# ==================== STUBS ====================

@login_required
def my_results(request):
    return render(request, 'dashboards/my_results.html', {'active': 'results'})


@login_required
def notifications(request):
    return render(request, 'dashboards/notifications.html', {'active': 'notifications'})

from accounts.forms import ProfileForm


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'dashboards/profile.html', {
        'form': form,
        'active': 'profile',
    })
 # ===================== admin dashboard elements ===========================
def _require_admin(request):
    """Return a redirect response if the user isn't an admin, else None."""
    if request.user.is_superuser:
        return redirect('/admin/')
    if request.user.role != User.Role.ADMIN:
        return redirect('competitor_dashboard')
    return None
#=============================== user managements ==========================================
@login_required
def admin_users(request):
    guard = _require_admin(request)
    if guard: return guard

    role_filter = request.GET.get('role')
    users = User.objects.all().order_by('-date_joined')
    if role_filter:
        users = users.filter(role=role_filter)

    return render(request, 'dashboards/admin_users.html', {
        'users': users,
        'role_filter': role_filter,
        'active': 'users',
    })

@login_required
def admin_toggle_user(request, user_id):
    guard = _require_admin(request)
    if guard:
        return guard

    target = get_object_or_404(User, id=user_id)

    if target.is_superuser:
        messages.error(request, "Cannot deactivate a superuser.")
    elif target == request.user:
        messages.error(request, "You cannot deactivate yourself.")
    else:
        target.is_active = not target.is_active
        target.save()
        state = "activated" if target.is_active else "deactivated"
        messages.success(request, f"User '{target.username}' {state}.")

    return redirect('admin_users')

@login_required
def admin_competitions(request):
    guard = _require_admin(request)
    if guard: return guard

    return render(request, 'dashboards/admin_competitions.html', {
        'competitions': Competition.objects.all().order_by('-created_at'),
        'active': 'competitions',
    })


@login_required
def admin_teams(request):
    guard = _require_admin(request)
    if guard: return guard

    return render(request, 'dashboards/admin_teams.html', {
        'teams': Team.objects.all().order_by('-created_at'),
        'active': 'teams',
    })

#======================handling the submission on the platform=======================
@login_required
def admin_submissions(request):
    guard = _require_admin(request)
    if guard: return guard

    qs = Submission.objects.select_related('team', 'competition').order_by('-submitted_at')

    comp_id = request.GET.get('competition')
    track = request.GET.get('track')
    sector = request.GET.get('sector')
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    late_only = request.GET.get('late')

    if comp_id:
        qs = qs.filter(competition_id=comp_id)
    if track:
        qs = qs.filter(competition__track=track)
    if sector:
        qs = qs.filter(team__sector=sector)
    if date_from:
        qs = qs.filter(submitted_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(submitted_at__date__lte=date_to)
    if late_only:
        qs = qs.filter(is_late=True)

    return render(request, 'dashboards/admin_submissions.html', {
        'submissions': qs,
        'competitions': Competition.objects.all(),
        'track_choices': Competition.Track.choices,
        'sector_choices': Team.Sector.choices,
        'filters': {
            'competition': comp_id or '',
            'track': track or '',
            'sector': sector or '',
            'from': date_from or '',
            'to': date_to or '',
            'late': late_only or '',
        },
        'active': 'submissions',
    })

@login_required
def admin_submission_detail(request, sub_id):
    guard = _require_admin(request)
    if guard:
        return guard

    sub = get_object_or_404(Submission, id=sub_id)

    return render(request, 'dashboards/admin_submission_detail.html', {
        'submission': sub,
        'active': 'submissions',
    })




@login_required
def admin_contacts(request):
    guard = _require_admin(request)
    if guard: return guard

    return render(request, 'dashboards/admin_contacts.html', {
        'messages_list': ContactMessage.objects.all(),
        'active': 'contacts',
    })

@login_required
def admin_evaluations(request):
    guard = _require_admin(request)
    if guard: return guard

    return render(request, 'dashboards/admin_evaluations.html', {'active': 'evaluations'})

# ============================ judge dashboard elements ====================================


