from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.urls import reverse

from .forms import CompetitorSignUpForm
from .models import User
from competitions.models import *
from competitions.forms import CompetitionForm
from submissions.models import *

def signup(request):
    initial = {}
    next_url = request.GET.get('next', '')
    if 'email' in request.GET:
        initial['email'] = request.GET['email']

    form = CompetitorSignUpForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.role = User.Role.COMPETITOR
        user.save()
        login(request, user)
        if next_url:
            return redirect(next_url)
        return redirect('competitor_dashboard')
    return render(request, 'accounts/signup.html', {'form': form, 'next': next_url})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return '/admin/'
        if user.role == User.Role.JUDGE:
            return reverse('judge_dashboard')
        if user.role == User.Role.ADMIN:
            return reverse('admin_dashboard')
        return reverse('competitor_dashboard')


def logout_view(request):
    logout(request)
    return redirect('login')

# comptetitor dashboard
@login_required
def competitor_dashboard(request):

    if request.user.is_superuser:
        return redirect('/admin/')

    teams = Team.objects.filter(members=request.user)
    submissions = Submission.objects.filter(team__in=teams)
    open_competitions = Competition.objects.filter(status=Competition.Status.OPEN)

    context = {
        'teams': teams,
        'submissions': submissions,
        'open_competitions': open_competitions,
    }
    return render(request, 'accounts/competitor_dashboard.html', context)


@login_required
def judge_dashboard(request):

    if request.user.is_superuser:
        return redirect('/admin/')
    return render(request, 'accounts/judge_dashboard.html')

#======================admin view ================================================
@login_required
def admin_dashboard(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    if request.user.role != User.Role.ADMIN:
        return redirect('competitor_dashboard')

    context = {
        'total_competitors': User.objects.filter(role=User.Role.COMPETITOR).count(),
        'total_judges': User.objects.filter(role=User.Role.JUDGE).count(),
        'total_teams': Team.objects.count(),
        'total_submissions': Submission.objects.count(),
        'users': User.objects.all().order_by('-date_joined'),
        'teams': Team.objects.all().order_by('-created_at'),
        'submissions': Submission.objects.all().order_by('-submitted_at'),
        'competitions': Competition.objects.all().order_by('-created_at'),
    }
    return render(request, 'accounts/admin_dashboard.html', context)


#============================== creating judges===================================
@login_required
def create_judge(request):
    if request.user.role != User.Role.ADMIN:
        return redirect('competitor_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
        else:
            User.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                role=User.Role.JUDGE,
            )
            messages.success(request, f"Judge '{username}' created.")
            return redirect('admin_dashboard')

    return render(request, 'accounts/create_judge.html')

# creating a competiton
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

    return render(request, 'accounts/create_competition.html', {'form': form})

@login_required
def create_admin(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    if request.user.role != User.Role.ADMIN:
        return redirect('competitor_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
        else:
            User.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                role=User.Role.ADMIN,
            )
            messages.success(request, f"Admin '{username}' created.")
            return redirect('admin_dashboard')

    return render(request, 'accounts/create_admin.html')