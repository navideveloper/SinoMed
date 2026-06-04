from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            from audit.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.LOGIN,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            return redirect('dashboard')
        else:
            messages.error(request, 'Username yoki parol noto\'g\'ri')

    return render(request, 'accounts/auth.html', {'tab': 'login'})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', User.Role.STUDENT)
        institution = request.POST.get('institution', '').strip()

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Bu username allaqachon band')
            return render(request, 'accounts/auth.html', {'tab': 'register'})

        if phone and User.objects.filter(phone=phone).exists():
            messages.error(request, 'Bu telefon raqam allaqachon ro\'yxatdan o\'tgan')
            return render(request, 'accounts/auth.html', {'tab': 'register'})

        names = full_name.split(' ', 1)
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=names[0],
            last_name=names[1] if len(names) > 1 else '',
            phone=phone or None,
            role=role,
            institution=institution,
        )

        from audit.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.REGISTER,
            ip_address=request.META.get('REMOTE_ADDR'),
            data={'role': role},
        )

        login(request, user)
        messages.success(request, 'Muvaffaqiyatli ro\'yxatdan o\'tdingiz!')
        return redirect('dashboard')

    return render(request, 'accounts/auth.html', {'tab': 'register'})


def logout_view(request):
    if request.user.is_authenticated:
        from audit.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.LOGOUT,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    logout(request)
    return redirect('index')
