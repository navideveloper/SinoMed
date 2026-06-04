import csv
import io
import json
import zipfile
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from analysis.models import Analysis
from .models import AnalysisLog, AuditLog


def _get_analysis_log_qs(user):
    """Return queryset scoped to user's access level."""
    qs = AnalysisLog.objects.select_related('analysis', 'analysis__user')
    if user.is_superuser:
        return qs
    if user.is_university:
        return qs.filter(institution=user.institution)
    if user.is_doctor:
        return qs.filter(analysis__user=user)
    return qs.none()


@login_required
def analysis_log_view(request):
    if not (request.user.is_superuser or request.user.is_university or request.user.is_doctor):
        return render(request, 'audit/access_denied.html', status=403)

    qs = _get_analysis_log_qs(request.user)

    # Filters
    model_type = request.GET.get('model_type', '')
    verdict = request.GET.get('verdict', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if model_type:
        qs = qs.filter(analysis__model_type=model_type)
    if verdict == 'flagged':
        qs = qs.filter(flagged_for_training=True)
    elif verdict == 'confirmed':
        qs = qs.filter(doctor_verdict=True)
    elif verdict == 'unreviewed':
        qs = qs.filter(doctor_verdict__isnull=True)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    # Stats
    stats_qs = _get_analysis_log_qs(request.user)
    this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stats = {
        'total': stats_qs.count(),
        'flagged': stats_qs.filter(flagged_for_training=True).count(),
        'avg_confidence': round(
            stats_qs.aggregate(a=Avg('ai_confidence'))['a'] or 0, 1
        ),
        'this_month': stats_qs.filter(created_at__gte=this_month).count(),
    }

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'audit/analysis_log.html', {
        'logs': page,
        'stats': stats,
        'model_types': Analysis.ModelType.choices,
        'filters': {
            'model_type': model_type,
            'verdict': verdict,
            'date_from': date_from,
            'date_to': date_to,
        },
    })


@login_required
def analysis_log_detail_view(request, pk):
    if not (request.user.is_superuser or request.user.is_university or request.user.is_doctor):
        return render(request, 'audit/access_denied.html', status=403)

    base_qs = _get_analysis_log_qs(request.user)
    log = get_object_or_404(base_qs, pk=pk)

    audit_events = AuditLog.objects.filter(
        analysis=log.analysis
    ).order_by('timestamp')

    return render(request, 'audit/analysis_log_detail.html', {
        'log': log,
        'audit_events': audit_events,
    })


@login_required
def audit_log_view(request):
    if not request.user.is_superuser:
        return render(request, 'audit/access_denied.html', status=403)

    qs = AuditLog.objects.select_related('user').all()

    username = request.GET.get('username', '')
    action = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if username:
        qs = qs.filter(user__username__icontains=username)
    if action:
        qs = qs.filter(action=action)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'audit/audit_log.html', {
        'logs': page,
        'actions': AuditLog.Action.choices,
        'filters': {
            'username': username,
            'action': action,
            'date_from': date_from,
            'date_to': date_to,
        },
    })


@login_required
def export_json_view(request):
    if not (request.user.is_superuser or request.user.is_university):
        return HttpResponse(status=403)

    qs = _get_analysis_log_qs(request.user)
    flagged_only = request.GET.get('flagged_only', 'true') == 'true'
    if flagged_only:
        qs = qs.filter(flagged_for_training=True)

    fmt = request.GET.get('format', 'json')

    records = list(qs.values(
        'id', 'analysis_id', 'analysis__model_type',
        'analysis__image', 'ai_diagnosis', 'ai_confidence',
        'ai_raw_output', 'doctor_verdict', 'doctor_note',
        'institution', 'created_at',
    ))

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="sinomed-export-{date.today()}.csv"'
        writer = csv.DictWriter(response, fieldnames=[
            'id', 'analysis_id', 'analysis__model_type', 'analysis__image',
            'ai_diagnosis', 'ai_confidence', 'doctor_verdict', 'doctor_note',
            'institution', 'created_at',
        ])
        writer.writeheader()
        for r in records:
            r.pop('ai_raw_output', None)
            writer.writerow(r)
        return response

    # JSON
    for r in records:
        r['created_at'] = r['created_at'].isoformat() if r['created_at'] else None
        r['model_type'] = r.pop('analysis__model_type', '')
        r['image_path'] = r.pop('analysis__image', '')
    response = HttpResponse(
        json.dumps(records, ensure_ascii=False, indent=2),
        content_type='application/json',
    )
    response['Content-Disposition'] = f'attachment; filename="sinomed-export-{date.today()}.json"'
    return response


@login_required
def export_zip_view(request):
    if not (request.user.is_superuser or request.user.is_university):
        return HttpResponse(status=403)

    qs = _get_analysis_log_qs(request.user).filter(flagged_for_training=True)
    institution_slug = (request.user.institution or 'all').replace(' ', '_')[:30]

    buf = io.BytesIO()
    annotations = []

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for log in qs.select_related('analysis'):
            img_field = log.analysis.image
            if img_field:
                try:
                    ext = img_field.name.rsplit('.', 1)[-1]
                    arcname = f'images/{log.analysis_id}.{ext}'
                    zf.write(img_field.path, arcname)
                except (FileNotFoundError, ValueError):
                    arcname = None
            else:
                arcname = None

            annotations.append({
                'id': log.pk,
                'analysis_id': log.analysis_id,
                'model_type': log.analysis.model_type,
                'image_file': arcname,
                'ai_diagnosis': log.ai_diagnosis,
                'ai_confidence': log.ai_confidence,
                'ai_raw_output': log.ai_raw_output,
                'doctor_note': log.doctor_note,
                'institution': log.institution,
                'created_at': log.created_at.isoformat(),
            })

        zf.writestr('annotations.json', json.dumps(annotations, ensure_ascii=False, indent=2))

    buf.seek(0)
    filename = f'sinomed-export-{institution_slug}-{date.today()}.zip'
    response = HttpResponse(buf.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
