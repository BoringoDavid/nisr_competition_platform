from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    # dashboard views url paths
    path('dashboard/', views.competitor_dashboard, name='competitor_dashboard'),
    path('judge/dashboard/', views.judge_dashboard, name='judge_dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('admin/dashboard/create-judge/', views.create_judge, name='create_judge'), # creating a judge
    path('admin/dashboard/create-competition/', views.create_competition, name='create_competition'), # creating a competition

    path('admin/dashboard/create-admin/', views.create_admin, name='create_admin'),
]