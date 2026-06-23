import json
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from .models import User, EmailToken
from apps.notifications.email import send_verify_email, send_password_reset


def _json(data, status=200):
    return JsonResponse(data, status=status)

def _err(msg, status=400):
    return JsonResponse({'ok': False, 'error': msg}, status=status)

def _ok(data=None):
    return JsonResponse({'ok': True, **(data or {})})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    if request.method == 'POST':
        d = json.loads(request.body)
        email = d.get('email','').strip().lower()
        username = d.get('username','').strip()
        password = d.get('password','')
        role = d.get('role', 'customer')
        first_name = d.get('first_name','').strip()
        last_name  = d.get('last_name','').strip()

        if not email or not password or not username:
            return _err('Email, username, and password are required.')
        if role not in ('customer', 'provider'):
            return _err('Invalid role.')
        if len(password) < 8:
            return _err('Password must be at least 8 characters.')
        if User.objects.filter(email=email).exists():
            return _err('An account with this email already exists.')
        if User.objects.filter(username=username).exists():
            return _err('Username already taken.')

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name,
            role=role, is_email_verified=False,
        )
        token = EmailToken.objects.create(user=user, purpose='verify')
        send_verify_email(user, token.token)
        return _ok({'message': 'Account created! Check your email to verify.'})
    return render(request, 'core/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    if request.method == 'POST':
        d = json.loads(request.body)
        email = d.get('email','').strip()
        password = d.get('password','')
        user = authenticate(request, username=email, password=password)
        if not user:
            # Try by email lookup
            try:
                u = User.objects.get(email=email)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass
        if not user:
            return _err('Invalid email or password.')
        if not user.is_email_verified:
            return _err('Please verify your email before logging in.')
        if not user.is_active:
            return _err('Your account has been deactivated.')
        login(request, user)
        next_url = d.get('next', '/dashboard/')
        return _ok({'redirect': next_url, 'role': user.role})
    return render(request, 'core/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('/')


def verify_email_view(request, token):
    try:
        et = EmailToken.objects.select_related('user').get(token=token, purpose='verify')
    except EmailToken.DoesNotExist:
        return render(request, 'core/verify_email.html', {'error': 'Invalid or expired link.'})
    if not et.is_valid:
        return render(request, 'core/verify_email.html', {'error': 'This link has expired.'})
    et.user.is_email_verified = True
    et.user.save()
    et.is_used = True
    et.save()
    return render(request, 'core/verify_email.html', {'success': True})


def resend_verify(request):
    if request.method == 'POST':
        d = json.loads(request.body)
        email = d.get('email','')
        try:
            user = User.objects.get(email=email)
            if not user.is_email_verified:
                token = EmailToken.objects.create(user=user, purpose='verify')
                send_verify_email(user, token.token)
        except User.DoesNotExist:
            pass
        return _ok({'message': 'If that account exists, a verification email was sent.'})
    return _err('POST required.')


def password_reset_request(request):
    if request.method == 'POST':
        d = json.loads(request.body)
        email = d.get('email','')
        try:
            user = User.objects.get(email=email)
            token = EmailToken.objects.create(user=user, purpose='reset')
            send_password_reset(user, token.token)
        except User.DoesNotExist:
            pass
        return _ok({'message': 'If that account exists, a reset email was sent.'})
    return render(request, 'core/login.html')


def password_reset_confirm(request, token):
    if request.method == 'POST':
        d = json.loads(request.body)
        try:
            et = EmailToken.objects.select_related('user').get(token=token, purpose='reset')
        except EmailToken.DoesNotExist:
            return _err('Invalid reset link.')
        if not et.is_valid:
            return _err('This reset link has expired.')
        pw = d.get('password','')
        if len(pw) < 8:
            return _err('Password must be at least 8 characters.')
        et.user.set_password(pw)
        et.user.save()
        et.is_used = True
        et.save()
        return _ok({'message': 'Password reset successfully!'})
    return render(request, 'core/reset_password.html', {'token': token})


@login_required
def me_view(request):
    u = request.user
    if request.method == 'PATCH':
        d = json.loads(request.body)
        for field in ('first_name','last_name','phone','bio','company_name','city','state',
                      'bank_name','bank_account_number','bank_account_name'):
            if field in d:
                setattr(u, field, d[field])
        u.save()
        return _ok({'message': 'Profile updated.'})
    return _json({
        'id': u.id, 'email': u.email, 'username': u.username,
        'first_name': u.first_name, 'last_name': u.last_name,
        'role': u.role, 'phone': u.phone, 'bio': u.bio,
        'company_name': u.company_name, 'city': u.city, 'state': u.state,
        'is_email_verified': u.is_email_verified,
        'is_provider_approved': u.is_provider_approved,
        'bank_name': u.bank_name,
        'bank_account_number': u.bank_account_number,
        'bank_account_name': u.bank_account_name,
        'avatar': u.avatar.url if u.avatar else None,
    })


@login_required
def change_password(request):
    if request.method == 'POST':
        d = json.loads(request.body)
        old_pw = d.get('old_password','')
        new_pw = d.get('new_password','')
        if not request.user.check_password(old_pw):
            return _err('Current password is incorrect.')
        if len(new_pw) < 8:
            return _err('New password must be at least 8 characters.')
        request.user.set_password(new_pw)
        request.user.save()
        update_session_auth_hash(request, request.user)
        return _ok({'message': 'Password changed.'})
    return _err('POST required.')
