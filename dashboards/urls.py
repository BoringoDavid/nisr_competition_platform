from django.urls import path
from . import views

urlpatterns = [
    path('', views.competitor_dashboard, name='competitor_dashboard'),
    path('judge/', views.judge_dashboard, name='judge_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
]