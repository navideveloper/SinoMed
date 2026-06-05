from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from analysis.models import Analysis


@login_required
def dashboard(request):
    user = request.user
    analyses = Analysis.objects.filter(user=user).select_related('result')[:10]

    total_analyses = Analysis.objects.filter(user=user, status=Analysis.Status.COMPLETED).count()

    from django.db.models import Avg
    avg_confidence = None
    if total_analyses:
        from analysis.models import AnalysisResult
        avg_confidence = AnalysisResult.objects.filter(
            analysis__user=user
        ).aggregate(avg=Avg('confidence'))['avg']

    from django.utils import timezone
    this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_analyses = Analysis.objects.filter(user=user, created_at__gte=this_month).count()

    leaderboard = []
    if user.is_doctor or user.is_student:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        leaderboard = User.objects.filter(
            role__in=[User.Role.DOCTOR, User.Role.STUDENT]
        ).annotate(
            total=Count('analyses', filter=Q(analyses__status=Analysis.Status.COMPLETED))
        ).order_by('-total')[:10]

    # Shifokor uchun: o'z muassasasidagi ko'rilmagan tahlillar
    pending_reviews = []
    if user.is_doctor and user.organization_id:
        from analysis.models import AnalysisResult
        pending_reviews = Analysis.objects.filter(
            user__organization_id=user.organization_id,
            status=Analysis.Status.COMPLETED,
            result__doctor_confirmed__isnull=True,
        ).select_related('user', 'result').order_by('-created_at')[:10]

    context = {
        'analyses': analyses,
        'total_analyses': total_analyses,
        'avg_confidence': round(avg_confidence, 1) if avg_confidence else 0,
        'month_analyses': month_analyses,
        'leaderboard': leaderboard,
        'pending_reviews': pending_reviews,
    }
    return render(request, 'dashboard/dashboard.html', context)
