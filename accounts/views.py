from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
import json as _json
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


@login_required
def user_list_view(request):
    if not (request.user.is_superuser or request.user.is_university):
        return redirect('dashboard')

    qs = User.objects.all().annotate(
        total_analyses=Count('analyses')
    ).order_by('-date_joined')

    if request.user.is_university and not request.user.is_superuser:
        qs = qs.filter(institution=request.user.institution)

    # Filters
    role_filter = request.GET.get('role', '')
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    if role_filter:
        qs = qs.filter(role=role_filter)
    if search:
        qs = qs.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(institution__icontains=search)
        )
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    # Stats
    base_qs = User.objects.all()
    if request.user.is_university and not request.user.is_superuser:
        base_qs = base_qs.filter(institution=request.user.institution)

    stats = {
        'total': base_qs.count(),
        'doctors': base_qs.filter(role='doctor').count(),
        'students': base_qs.filter(role='student').count(),
        'universities': base_qs.filter(role='university').count(),
        'inactive': base_qs.filter(is_active=False).count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/users.html', {
        'users': page,
        'stats': stats,
        'roles': User.Role.choices,
        'filters': {
            'role': role_filter,
            'search': search,
            'status': status_filter,
        },
    })


@login_required
def user_detail_view(request, pk):
    if not (request.user.is_superuser or request.user.is_university):
        return redirect('dashboard')

    target_user = get_object_or_404(User, pk=pk)

    # University can only see own institution users
    if request.user.is_university and not request.user.is_superuser:
        if target_user.institution != request.user.institution:
            return redirect('user_list')

    from analysis.models import Analysis
    recent_analyses = Analysis.objects.filter(
        user=target_user
    ).select_related('result').order_by('-created_at')[:10]

    from audit.models import AuditLog
    recent_audit = AuditLog.objects.filter(user=target_user).order_by('-timestamp')[:10]

    return render(request, 'accounts/user_detail.html', {
        'target_user': target_user,
        'recent_analyses': recent_analyses,
        'recent_audit': recent_audit,
        'total_analyses': Analysis.objects.filter(user=target_user).count(),
    })


@login_required
@require_POST
def user_toggle_active(request, pk):
    if not (request.user.is_superuser or request.user.is_university):
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    target_user = get_object_or_404(User, pk=pk)

    if request.user.is_university and not request.user.is_superuser:
        if target_user.institution != request.user.institution:
            return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    # Cannot deactivate superusers
    if target_user.is_superuser:
        return JsonResponse({'error': 'Superuserni o\'chirib bo\'lmaydi'}, status=400)

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])

    return JsonResponse({
        'is_active': target_user.is_active,
        'message': 'Faollashtirildi' if target_user.is_active else 'O\'chirildi'
    })


@login_required
@require_POST
def user_update_balance(request, pk):
    """Superuser only — add/subtract balance"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Faqat superuser'}, status=403)

    target_user = get_object_or_404(User, pk=pk)

    try:
        data = _json.loads(request.body)
        amount = float(data.get('amount', 0))
    except (ValueError, KeyError):
        return JsonResponse({'error': 'Noto\'g\'ri summa'}, status=400)

    target_user.balance += amount
    if target_user.balance < 0:
        target_user.balance = 0
    target_user.save(update_fields=['balance'])

    return JsonResponse({
        'balance': float(target_user.balance),
        'message': f'Balans yangilandi: {target_user.balance:,.0f} so\'m'
    })
