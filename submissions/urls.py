from django.urls import path
from . import views

urlpatterns = [
    path('team/<int:team_id>/submit/', views.submit, name='submit'),
]