from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

User = get_user_model()


def landing(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('/admin/')
        if request.user.role == User.Role.JUDGE:
            return redirect('judge_dashboard')
        if request.user.role == User.Role.ADMIN:
            return redirect('admin_dashboard')
        return redirect('competitor_dashboard')
    return render(request, 'public/landing.html')


def competition_undergraduate(request):
    return render(request, 'public/competition_undergraduate.html')


def competition_high_school(request):
    return render(request, 'public/competition_high_school.html')


def past_competitions(request):
    return render(request, 'public/past_competitions.html')


def testimonials(request):
    return render(request, 'public/testimonials.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')

        full_message = f"""
New contact message from NISR Competition Platform

Name: {name}
Email: {email}

Message:
{message_body}
"""
        send_mail(
            subject=f"[Contact] {subject}",
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            reply_to=[email],
        )
        messages.success(request, "Your message has been sent. We'll get back to you soon.")
        return redirect('contact')

    return render(request, 'public/contact.html')