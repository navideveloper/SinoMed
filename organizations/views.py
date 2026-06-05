from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator

from .models import Organization
from accounts.models import User


def _require_org_admin(view_func):
    """Decorator: only org_admin or superuser can access."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_superuser or request.user.is_org_admin):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@_require_org_admin
def org_dashboard(request):
    """Organization admin dashboard: pending requests, stats, recent activity."""
    if request.user.is_superuser:
        org = None
        base_members = User.objects.exclude(is_superuser=True)
    else:
        org = request.user.organization
        if not org:
            return render(request, 'organizations/no_org.html')
        base_members = org.members.all()

    pending_users = base_members.filter(approval_status='pending').order_by('-date_joined')[:20]
    recent_approved = base_members.filter(
        approval_status='approved'
    ).order_by('-date_joined')[:5]

    stats = {
        'pending': base_members.filter(approval_status='pending').count(),
        'approved': base_members.filter(approval_status='approved').count(),
        'rejected': base_members.filter(approval_status='rejected').count(),
        'doctors': base_members.filter(role='doctor', approval_status='approved').count(),
        'students': base_members.filter(role='student', approval_status='approved').count(),
    }

    from audit.models import AnalysisLog, AuditLog
    if request.user.is_superuser:
        recent_analyses = AnalysisLog.objects.select_related(
            'analysis__user'
        ).order_by('-created_at')[:10]
        recent_audit = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    else:
        recent_analyses = AnalysisLog.objects.filter(
            institution=org.name
        ).select_related('analysis__user').order_by('-created_at')[:10]
        recent_audit = AuditLog.objects.filter(
            user__organization=org
        ).select_related('user').order_by('-timestamp')[:10]

    all_orgs = Organization.objects.filter(is_active=True) if request.user.is_superuser else None

    return render(request, 'organizations/dashboard.html', {
        'org': org,
        'pending_users': pending_users,
        'recent_approved': recent_approved,
        'stats': stats,
        'recent_analyses': recent_analyses,
        'recent_audit': recent_audit,
        'all_orgs': all_orgs,
    })


@login_required
@require_POST
def approve_user(request, pk):
    """Approve a pending registration request."""
    if not (request.user.is_superuser or request.user.is_org_admin):
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    target_user = get_object_or_404(User, pk=pk)

    # Org admin can only approve members of own org
    if request.user.is_org_admin and not request.user.is_superuser:
        if target_user.organization != request.user.organization:
            return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    target_user.approval_status = User.ApprovalStatus.APPROVED
    target_user.is_active = True
    target_user.rejection_reason = ''
    target_user.save(update_fields=['approval_status', 'is_active', 'rejection_reason'])

    from audit.models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action=AuditLog.Action.DOCTOR_CONFIRM,  # reuse action for approval event
        ip_address=request.META.get('REMOTE_ADDR'),
        data={'approved_user': target_user.username, 'approved_user_id': target_user.pk},
    )

    return JsonResponse({
        'status': 'approved',
        'message': f'{target_user.get_full_name() or target_user.username} tasdiqlandi'
    })


@login_required
@require_POST
def reject_user(request, pk):
    """Reject a pending registration request."""
    if not (request.user.is_superuser or request.user.is_org_admin):
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    target_user = get_object_or_404(User, pk=pk)

    if request.user.is_org_admin and not request.user.is_superuser:
        if target_user.organization != request.user.organization:
            return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    import json
    try:
        body = json.loads(request.body)
        reason = body.get('reason', '').strip()
    except Exception:
        reason = ''

    target_user.approval_status = User.ApprovalStatus.REJECTED
    target_user.is_active = False
    target_user.rejection_reason = reason
    target_user.save(update_fields=['approval_status', 'is_active', 'rejection_reason'])

    return JsonResponse({
        'status': 'rejected',
        'message': f'{target_user.get_full_name() or target_user.username} rad etildi'
    })
