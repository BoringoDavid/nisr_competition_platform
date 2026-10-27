from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_competition, name='create_competition'),
    path('invitation/<uuid:token>/', views.accept_invitation, name='accept_invitation'),
    path('create/', views.create_competition, name='create_competition'),
]