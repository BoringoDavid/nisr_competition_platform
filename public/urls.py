from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='home'),
    path('competition/undergraduate/', views.competition_undergraduate, name='competition_undergraduate'),
    path('competition/high-school/', views.competition_high_school, name='competition_high_school'),
    path('past-competitions/', views.past_competitions, name='past_competitions'),
    path('testimonials/', views.testimonials, name='testimonials'),
    path('contact/', views.contact, name='contact'),
]