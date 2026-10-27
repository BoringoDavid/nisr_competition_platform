from django.urls import path
from . import views

urlpatterns = [
    path('', views.competitor_dashboard, name='competitor_dashboard'),
    path('judge/', views.judge_dashboard, name='judge_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),

    # Teams
    path('teams/', views.my_team, name='my_team'),
    path('teams/create/', views.create_team, name='create_team'),
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
    path('teams/<int:team_id>/invite/', views.invite_member, name='invite_member'),
    path('teams/<int:team_id>/submit/', views.submit, name='submit'),

    # Submissions
    path('submissions/', views.my_submissions, name='my_submissions'),
    path('admin/submissions/<int:sub_id>/', views.admin_submission_detail, name='admin_submission_detail'),

    # Competitions
    path('competitions/', views.browse_competitions, name='browse_competitions'),

    # Results / Notifications / Profile
    path('results/', views.my_results, name='my_results'),
    path('notifications/', views.notifications, name='notifications'),
    path('profile/', views.profile, name='profile'),


    # Admin
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/toggle/', views.admin_toggle_user, name='admin_toggle_user'),
    path('admin/competitions/', views.admin_competitions, name='admin_competitions'),
    path('admin/teams/', views.admin_teams, name='admin_teams'),
    path('admin/submissions/', views.admin_submissions, name='admin_submissions'),
    path('admin/evaluations/', views.admin_evaluations, name='admin_evaluations'),
    path('admin/contacts/', views.admin_contacts, name='admin_contacts'),
]