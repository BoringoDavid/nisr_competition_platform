from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/dashboard/profile/'
    ), name='password_change'),
    # Admin user management
    path('admin/dashboard/create-judge/', views.create_judge, name='create_judge'),
    path('admin/dashboard/create-admin/', views.create_admin, name='create_admin'),

]