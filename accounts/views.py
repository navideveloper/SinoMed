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
from organizations.models import Organization


# ── Auth ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Try to authenticate (works even for inactive users)
        try:
            raw_user = User.objects.get(username=username)
        except User.DoesNotExist:
            raw_user = None

        if raw_user is not None and raw_user.check_password(password):
            if raw_user.is_pending:
                return render(request, 'accounts/auth.html', {
                    'tab': 'login',
                    'status_message': 'pending',
                    'org_name': raw_user.org_name,
                })
            if raw_user.is_rejected:
                return render(request, 'accounts/auth.html', {
                    'tab': 'login',
                    'status_message': 'rejected',
                    'rejection_reason': raw_user.rejection_reason,
                })
            if not raw_user.is_active:
                messages.error(request, 'Hisobingiz o\'chirilgan. Admin bilan bog\'laning.')
                return render(request, 'accounts/auth.html', {'tab': 'login'})

            login(request, raw_user)
            from audit.models import AuditLog
            AuditLog.objects.create(
                user=raw_user,
                action=AuditLog.Action.LOGIN,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            return _redirect_by_role(raw_user)
        else:
            messages.error(request, 'Username yoki parol noto\'g\'ri')

    return render(request, 'accounts/auth.html', {'tab': 'login'})


def register_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', '')
        org_id = request.POST.get('organization_id', '').strip()

        # Validate role
        if role not in (User.Role.STUDENT, User.Role.DOCTOR):
            messages.error(request, 'Noto\'g\'ri rol tanlandi')
            return render(request, 'accounts/auth.html', {'tab': 'register'})

        # Validate organization
        try:
            organization = Organization.objects.get(pk=org_id, is_active=True)
        except (Organization.DoesNotExist, ValueError):
            messages.error(request, 'Muassasani to\'g\'ri tanlang')
            return render(request, 'accounts/auth.html', {'tab': 'register'})

        # Check role ↔ org type match
        if role == User.Role.STUDENT and organization.org_type != Organization.OrgType.UNIVERSITY:
            messages.error(request, 'Talabalar faqat universitetni tanlashi mumkin')
            return render(request, 'accounts/auth.html', {'tab': 'register'})
        if role == User.Role.DOCTOR and organization.org_type != Organization.OrgType.HOSPITAL:
            messages.error(request, 'Shifokorlar faqat kasalxonani tanlashi mumkin')
            return render(request, 'accounts/auth.html', {'tab': 'register'})

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
            organization=organization,
            institution=organization.name,  # sync legacy field
            # New users start as inactive/pending — admin must approve
            is_active=False,
            approval_status=User.ApprovalStatus.PENDING,
        )

        from audit.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.REGISTER,
            ip_address=request.META.get('REMOTE_ADDR'),
            data={'role': role, 'organization': organization.name},
        )

        # Show "waiting for approval" page
        return render(request, 'accounts/auth.html', {
            'tab': 'login',
            'status_message': 'registered',
            'org_name': organization.name,
        })

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


def api_organizations(request):
    """Return organizations list filtered by role (for registration form AJAX)."""
    role = request.GET.get('role', '')
    if role == User.Role.STUDENT:
        org_type = Organization.OrgType.UNIVERSITY
    elif role == User.Role.DOCTOR:
        org_type = Organization.OrgType.HOSPITAL
    else:
        return JsonResponse({'organizations': []})

    orgs = Organization.objects.filter(org_type=org_type, is_active=True).values(
        'id', 'name', 'code', 'address'
    )
    return JsonResponse({'organizations': list(orgs)})


def _redirect_by_role(user):
    """Redirect user to appropriate dashboard based on role."""
    if user.is_superuser:
        return redirect('dashboard')  # superuser sees full dashboard
    if user.is_org_admin:
        return redirect('org_dashboard')
    return redirect('dashboard')


# ── User Management (org_admin / superuser) ─────────────────────────────────

@login_required
def user_list_view(request):
    if not (request.user.is_superuser or request.user.is_org_admin):
        return redirect('dashboard')

    qs = User.objects.all().annotate(
        total_analyses=Count('analyses')
    ).order_by('-date_joined')

    if request.user.is_org_admin and not request.user.is_superuser:
        qs = qs.filter(organization=request.user.organization)

    # Filters
    role_filter = request.GET.get('role', '')
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    approval_filter = request.GET.get('approval', '')

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
    if approval_filter:
        qs = qs.filter(approval_status=approval_filter)

    # Stats
    base_qs = User.objects.all()
    if request.user.is_org_admin and not request.user.is_superuser:
        base_qs = base_qs.filter(organization=request.user.organization)

    stats = {
        'total': base_qs.count(),
        'doctors': base_qs.filter(role='doctor').count(),
        'students': base_qs.filter(role='student').count(),
        'pending': base_qs.filter(approval_status='pending').count(),
        'inactive': base_qs.filter(is_active=False).count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/users.html', {
        'users': page,
        'stats': stats,
        'roles': [(r.value, r.label) for r in User.Role if r != User.Role.ORG_ADMIN],
        'approval_choices': User.ApprovalStatus.choices,
        'filters': {
            'role': role_filter,
            'search': search,
            'status': status_filter,
            'approval': approval_filter,
        },
    })


@login_required
def user_detail_view(request, pk):
    if not (request.user.is_superuser or request.user.is_org_admin):
        return redirect('dashboard')

    target_user = get_object_or_404(User, pk=pk)

    # Org admin can only see own institution users
    if request.user.is_org_admin and not request.user.is_superuser:
        if target_user.organization != request.user.organization:
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
    if not (request.user.is_superuser or request.user.is_org_admin):
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    target_user = get_object_or_404(User, pk=pk)

    if request.user.is_org_admin and not request.user.is_superuser:
        if target_user.organization != request.user.organization:
            return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

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


# ── SuperAdmin full CRUD ─────────────────────────────────────────────────────

@login_required
def user_create_view(request):
    """SuperAdmin: create any user. Org admin: create student/doctor for own org."""
    if not (request.user.is_superuser or request.user.is_org_admin):
        return redirect('dashboard')

    from organizations.models import Organization
    is_org_admin_creating = request.user.is_org_admin and not request.user.is_superuser

    if is_org_admin_creating:
        organizations = Organization.objects.filter(
            pk=request.user.organization_id, is_active=True
        )
        roles = [(r.value, r.label) for r in User.Role
                 if r not in (User.Role.ORG_ADMIN,)]
    else:
        organizations = Organization.objects.filter(is_active=True).order_by('name')
        roles = User.Role.choices

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', '')

        # org_admin: force own org, block superuser escalation
        if is_org_admin_creating:
            org_id = str(request.user.organization_id or '')
            is_superuser_flag = False
            approval_status = User.ApprovalStatus.APPROVED
            balance = '0'
            # Prevent role abuse: only student/doctor allowed
            if role not in (User.Role.STUDENT, User.Role.DOCTOR):
                error = 'Faqat talaba yoki shifokor yaratish mumkin'
        else:
            org_id = request.POST.get('organization_id', '').strip()
            is_superuser_flag = request.POST.get('is_superuser') == 'on'
            approval_status = request.POST.get('approval_status', User.ApprovalStatus.APPROVED)
            balance = request.POST.get('balance', '0').strip()

        if not error:
            if User.objects.filter(username=username).exists():
                error = 'Bu username allaqachon band'
            elif phone and User.objects.filter(phone=phone).exists():
                error = 'Bu telefon raqam allaqachon ro\'yxatdan o\'tgan'
            else:
                organization = None
                if org_id:
                    try:
                        organization = Organization.objects.get(pk=org_id)
                    except Organization.DoesNotExist:
                        pass

                names = full_name.split(' ', 1) if full_name else ['', '']
                try:
                    bal = float(balance or 0)
                except ValueError:
                    bal = 0.0

                user_obj = User.objects.create_user(
                    username=username,
                    password=password or User.objects.make_random_password(16),
                    first_name=names[0],
                    last_name=names[1] if len(names) > 1 else '',
                    phone=phone or None,
                    role=role,
                    organization=organization,
                    institution=organization.name if organization else '',
                    balance=bal,
                    is_active=True,
                    approval_status=approval_status,
                    is_superuser=is_superuser_flag,
                    is_staff=is_superuser_flag,
                )

                from audit.models import AuditLog
                creator_label = 'org_admin' if is_org_admin_creating else 'superadmin'
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.Action.REGISTER,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    data={'created_user': user_obj.username, 'role': role, 'by': creator_label},
                )
                messages.success(request, f'Foydalanuvchi "{user_obj.username}" yaratildi')
                return redirect('user_detail', pk=user_obj.pk)

    return render(request, 'accounts/user_form.html', {
        'mode': 'create',
        'organizations': organizations,
        'roles': roles,
        'approval_choices': User.ApprovalStatus.choices,
        'error': error,
        'is_org_admin_creating': is_org_admin_creating,
    })


@login_required
def user_edit_view(request, pk):
    """SuperAdmin: edit any user. Org admin: edit own-org members."""
    if not (request.user.is_superuser or request.user.is_org_admin):
        return redirect('dashboard')

    target_user = get_object_or_404(User, pk=pk)

    if request.user.is_org_admin and not request.user.is_superuser:
        if target_user.organization != request.user.organization:
            return redirect('user_list')

    from organizations.models import Organization
    organizations = Organization.objects.filter(is_active=True).order_by('name')

    error = None
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', target_user.role)
        org_id = request.POST.get('organization_id', '').strip()
        approval_status = request.POST.get('approval_status', target_user.approval_status)
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        new_password = request.POST.get('new_password', '').strip()

        # Superuser-only fields
        if request.user.is_superuser:
            balance = request.POST.get('balance', str(target_user.balance)).strip()
            is_superuser_flag = request.POST.get('is_superuser') == 'on'
        else:
            balance = str(target_user.balance)
            is_superuser_flag = target_user.is_superuser

        # Check phone uniqueness
        if phone and User.objects.filter(phone=phone).exclude(pk=pk).exists():
            error = 'Bu telefon raqam boshqa foydalanuvchida bor'
        else:
            names = full_name.split(' ', 1) if full_name else [target_user.first_name, target_user.last_name]
            target_user.first_name = names[0]
            target_user.last_name = names[1] if len(names) > 1 else ''
            target_user.phone = phone or None
            target_user.approval_status = approval_status
            target_user.rejection_reason = rejection_reason

            if request.user.is_superuser:
                target_user.role = role
                target_user.is_superuser = is_superuser_flag
                target_user.is_staff = is_superuser_flag
                try:
                    target_user.balance = float(balance or 0)
                except ValueError:
                    pass

            if org_id:
                try:
                    org = Organization.objects.get(pk=org_id)
                    target_user.organization = org
                    target_user.institution = org.name
                except Organization.DoesNotExist:
                    pass

            # Update is_active based on approval_status
            if approval_status == User.ApprovalStatus.APPROVED:
                target_user.is_active = True
            elif approval_status == User.ApprovalStatus.REJECTED:
                target_user.is_active = False

            if new_password:
                target_user.set_password(new_password)

            target_user.save()
            messages.success(request, f'"{target_user.username}" ma\'lumotlari yangilandi')
            return redirect('user_detail', pk=pk)

    return render(request, 'accounts/user_form.html', {
        'mode': 'edit',
        'target_user': target_user,
        'organizations': organizations,
        'roles': User.Role.choices,
        'approval_choices': User.ApprovalStatus.choices,
        'error': error,
    })


@login_required
@require_POST
def user_delete_view(request, pk):
    """SuperAdmin only: hard-delete a user."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Faqat superuser'}, status=403)

    target_user = get_object_or_404(User, pk=pk)
    if target_user.is_superuser:
        return JsonResponse({'error': 'Superuserni o\'chirib bo\'lmaydi'}, status=400)

    username = target_user.username
    target_user.delete()

    messages.success(request, f'"{username}" o\'chirildi')
    return JsonResponse({'deleted': True, 'message': f'"{username}" o\'chirildi'})
