from django.urls import path
from . import views

urlpatterns = [
    path('team/create/', views.create_team, name='create_team'),
    path('team/my/', views.my_team, name='my_team'),
    path('team/<int:team_id>/invite/', views.invite_member, name='invite_member'),
]