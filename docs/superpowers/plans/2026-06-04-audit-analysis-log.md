# Audit & Analysis Log System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `AnalysisLog` model to record every AI analysis with full output, auto-flag doctor-corrected results, and expose filtered views + export for university/superuser roles.

**Architecture:** New `AnalysisLog` model lives in the `audit` app alongside `AuditLog`. `AuditLog` keeps security events (login/logout/register/payment); `AnalysisLog` owns all AI analysis records. Five new views in `audit/views.py` handle list, detail, and export. Access is scoped: superuser sees all, university sees own institution, doctor sees own reviewed analyses.

**Tech Stack:** Django 6.0.6, Python 3.13, stdlib `zipfile` + `csv` + `json` for export, Django Paginator, existing dark-blue CSS variable system.

**Run server with:** `C:\Python313\python.exe manage.py runserver 8002`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `audit/models.py` | Add `AnalysisLog` model |
| Modify | `audit/admin.py` | Register `AuditLog` + `AnalysisLog` |
| Modify | `billing/admin.py` | Register `Plan`, `Subscription`, `Payment` |
| Modify | `analysis/views.py` | Write `AnalysisLog` in `api_analyze` + `result_detail` |
| Create | `audit/views.py` | 5 views: list, detail, audit_log, export_json, export_zip |
| Create | `audit/urls.py` | 5 URL patterns |
| Modify | `config/urls.py` | Include `audit.urls` |
| Create | `templates/audit/analysis_log.html` | Filterable log table + stats + export buttons |
| Create | `templates/audit/analysis_log_detail.html` | Single log detail + timeline |
| Create | `templates/audit/audit_log.html` | Security events table (superuser only) |
| Modify | `templates/dashboard/dashboard.html` | Flagged stat card for university/superuser |

---

## Task 1: Add `AnalysisLog` model and migrate

**Files:**
- Modify: `audit/models.py`

- [ ] **Step 1: Add `AnalysisLog` to `audit/models.py`**

Replace the entire file content:

```python
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'login', 'Tizimga kirish'
        LOGOUT = 'logout', 'Tizimdan chiqish'
        REGISTER = 'register', "Ro'yxatdan o'tish"
        UPLOAD = 'upload', 'Rasm yuklash'
        ANALYZE = 'analyze', 'Tahlil boshlash'  # legacy — new code uses AnalysisLog
        RESULT_VIEW = 'result_view', "Natijani ko'rish"
        DOCTOR_CONFIRM = 'doctor_confirm', 'Shifokor tasdiqladi'
        DOCTOR_REPORT = 'doctor_report', 'AI xatosi hisoboti'
        PAYMENT = 'payment', "To'lov"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    analysis = models.ForeignKey(
        'analysis.Analysis', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Audit log'
        verbose_name_plural = 'Audit loglar'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.user} — {self.get_action_display()} ({self.timestamp:%d.%m.%Y %H:%M})'


class AnalysisLog(models.Model):
    class ErrorType(models.TextChoices):
        LOW_CONFIDENCE = 'low_confidence', 'Past ishonch'
        SERVICE_ERROR = 'service_error', 'Servis xatosi'
        TIMEOUT = 'timeout', 'Vaqt tugadi'

    analysis = models.OneToOneField(
        'analysis.Analysis', on_delete=models.CASCADE,
        related_name='analysis_log'
    )
    ai_diagnosis = models.CharField(max_length=255, blank=True)
    ai_confidence = models.FloatField(default=0.0)
    ai_raw_output = models.JSONField(default=dict)
    error_type = models.CharField(
        max_length=30, choices=ErrorType.choices, null=True, blank=True
    )
    error_detail = models.TextField(blank=True)

    doctor_verdict = models.BooleanField(null=True, blank=True)
    doctor_note = models.TextField(blank=True)
    flagged_for_training = models.BooleanField(default=False)

    institution = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tahlil logi'
        verbose_name_plural = 'Tahlil loglari'
        ordering = ['-created_at']

    def __str__(self):
        flag = ' 🔴' if self.flagged_for_training else ''
        return f'{self.analysis} — {self.ai_confidence:.1f}%{flag}'
```

- [ ] **Step 2: Run migrations**

```
C:\Python313\python.exe manage.py makemigrations audit
C:\Python313\python.exe manage.py migrate
```

Expected output:
```
Migrations for 'audit':
  audit/migrations/0002_analysislog.py
    - Create model AnalysisLog
Operations to perform:
  Apply all migrations: ...
Running migrations:
  Applying audit.0002_analysislog... OK
```

- [ ] **Step 3: Commit**

```
git add audit/models.py audit/migrations/0002_analysislog.py
git commit -m "feat(audit): add AnalysisLog model for AI analysis tracking"
```

---

## Task 2: Register models in admin

**Files:**
- Modify: `audit/admin.py`
- Modify: `billing/admin.py`

- [ ] **Step 1: Update `audit/admin.py`**

```python
from django.contrib import admin
from .models import AuditLog, AnalysisLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    list_filter = ('action',)
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)


@admin.register(AnalysisLog)
class AnalysisLogAdmin(admin.ModelAdmin):
    list_display = ('analysis', 'ai_diagnosis', 'ai_confidence', 'doctor_verdict', 'flagged_for_training', 'institution', 'created_at')
    list_filter = ('flagged_for_training', 'doctor_verdict', 'error_type')
    search_fields = ('institution', 'ai_diagnosis')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
```

- [ ] **Step 2: Update `billing/admin.py`**

```python
from django.contrib import admin
from .models import Plan, Subscription, Payment


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('plan_type', 'price', 'duration_days', 'is_active')
    list_filter = ('is_active',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date')
    list_filter = ('status',)
    search_fields = ('user__username',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username',)
```

- [ ] **Step 3: Commit**

```
git add audit/admin.py billing/admin.py
git commit -m "chore(admin): register AuditLog, AnalysisLog, billing models in admin"
```

---

## Task 3: Write `AnalysisLog` in `analysis/views.py`

**Files:**
- Modify: `analysis/views.py`

- [ ] **Step 1: Update `api_analyze` — create AnalysisLog on success**

In `api_analyze`, replace the block after `result = AnalysisResult.objects.create(...)` (success path, lines 89–99) and the error block (lines 101–113). Then replace the AuditLog block at the end. Full updated function:

```python
@login_required
@require_POST
def api_analyze(request):
    try:
        data = json.loads(request.body)
        analysis_id = data.get('analysis_id')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    analysis = get_object_or_404(Analysis, pk=analysis_id, user=request.user)

    if hasattr(analysis, 'result'):
        return JsonResponse(_result_to_dict(analysis.result))

    analysis.status = Analysis.Status.PROCESSING
    analysis.save(update_fields=['status'])

    from audit.models import AuditLog, AnalysisLog
    error_type = None
    error_detail = ''

    try:
        ai_url = f"{settings.AI_SERVICE_URL}/predict"
        image_path = analysis.image.path

        with open(image_path, 'rb') as f:
            image_data = f.read()

        req = urllib.request.Request(
            ai_url,
            data=image_data,
            headers={
                'Content-Type': 'application/octet-stream',
                'X-Model-Type': analysis.model_type,
            },
            method='POST',
        )

        with urllib.request.urlopen(req, timeout=settings.AI_SERVICE_TIMEOUT) as resp:
            ai_response = json.loads(resp.read().decode())

        result = AnalysisResult.objects.create(
            analysis=analysis,
            diagnosis=ai_response.get('diagnosis', 'Noma\'lum'),
            diagnosis_type=ai_response.get('diagnosis_type', 'warning'),
            confidence=ai_response.get('confidence', 0.0),
            note=ai_response.get('note', ''),
            raw_output=ai_response,
        )

        analysis.status = Analysis.Status.COMPLETED
        analysis.save(update_fields=['status'])

        AnalysisLog.objects.create(
            analysis=analysis,
            ai_diagnosis=result.diagnosis,
            ai_confidence=result.confidence,
            ai_raw_output=ai_response,
            institution=request.user.institution,
        )

    except TimeoutError as e:
        error_type = AnalysisLog.ErrorType.TIMEOUT
        error_detail = str(e)
        analysis.status = Analysis.Status.ERROR
        analysis.save(update_fields=['status'])
        result = AnalysisResult.objects.create(
            analysis=analysis,
            diagnosis="Tahlil qilib bo'lmadi",
            diagnosis_type=AnalysisResult.DiagnosisType.WARNING,
            confidence=0.0,
            note=str(e),
            raw_output={'error': str(e)},
        )
        AnalysisLog.objects.create(
            analysis=analysis,
            ai_diagnosis='',
            ai_confidence=0.0,
            ai_raw_output={'error': str(e)},
            error_type=error_type,
            error_detail=error_detail,
            institution=request.user.institution,
        )

    except Exception as e:
        error_type = AnalysisLog.ErrorType.SERVICE_ERROR
        error_detail = str(e)
        analysis.status = Analysis.Status.ERROR
        analysis.save(update_fields=['status'])
        result = AnalysisResult.objects.create(
            analysis=analysis,
            diagnosis="Tahlil qilib bo'lmadi",
            diagnosis_type=AnalysisResult.DiagnosisType.WARNING,
            confidence=0.0,
            note=str(e),
            raw_output={'error': str(e)},
        )
        AnalysisLog.objects.create(
            analysis=analysis,
            ai_diagnosis='',
            ai_confidence=0.0,
            ai_raw_output={'error': str(e)},
            error_type=error_type,
            error_detail=error_detail,
            institution=request.user.institution,
        )

    AuditLog.objects.create(
        user=request.user,
        action=AuditLog.Action.UPLOAD,
        analysis=analysis,
        ip_address=request.META.get('REMOTE_ADDR'),
        data={'model_type': analysis.model_type},
    )

    return JsonResponse(_result_to_dict(result))
```

- [ ] **Step 2: Update `result_detail` — sync AnalysisLog when doctor reviews**

Replace the `result_detail` view:

```python
@login_required
def result_detail(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk, user=request.user)

    if request.method == 'POST' and request.user.is_doctor:
        action = request.POST.get('action')
        result = analysis.result
        from django.utils import timezone
        from audit.models import AuditLog, AnalysisLog

        if action == 'confirm':
            result.doctor_confirmed = True
            result.doctor_note = request.POST.get('note', '')
            result.reviewed_by = request.user
            result.reviewed_at = timezone.now()
            result.save()
            AuditLog.objects.create(
                user=request.user, action=AuditLog.Action.DOCTOR_CONFIRM,
                analysis=analysis, ip_address=request.META.get('REMOTE_ADDR'),
            )
            AnalysisLog.objects.filter(analysis=analysis).update(
                doctor_verdict=True,
                doctor_note=result.doctor_note,
            )

        elif action == 'report':
            result.doctor_confirmed = False
            result.doctor_report = request.POST.get('report', '')
            result.reviewed_by = request.user
            result.reviewed_at = timezone.now()
            result.save()
            AuditLog.objects.create(
                user=request.user, action=AuditLog.Action.DOCTOR_REPORT,
                analysis=analysis, ip_address=request.META.get('REMOTE_ADDR'),
                data={'report': result.doctor_report},
            )
            AnalysisLog.objects.filter(analysis=analysis).update(
                doctor_verdict=False,
                doctor_note=result.doctor_report,
                flagged_for_training=True,
            )

        return redirect('result_detail', pk=pk)

    context = {
        'analysis': analysis,
        'result': getattr(analysis, 'result', None),
    }
    return render(request, 'analysis/result.html', context)
```

- [ ] **Step 3: Commit**

```
git add analysis/views.py
git commit -m "feat(analysis): write AnalysisLog on every AI call and doctor review"
```

---

## Task 4: Create `audit/views.py`

**Files:**
- Create: `audit/views.py`

- [ ] **Step 1: Write all 5 views**

Create `audit/views.py`:

```python
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

    # Stats (superuser only gets global stats; others get scoped)
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
```

- [ ] **Step 2: Commit**

```
git add audit/views.py
git commit -m "feat(audit): add analysis log, audit log, and export views"
```

---

## Task 5: Create `audit/urls.py` and wire into `config/urls.py`

**Files:**
- Create: `audit/urls.py`
- Modify: `config/urls.py`

- [ ] **Step 1: Create `audit/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.audit_log_view, name='audit_log'),
    path('analyses/', views.analysis_log_view, name='analysis_log'),
    path('analyses/<int:pk>/', views.analysis_log_detail_view, name='analysis_log_detail'),
    path('export/json/', views.export_json_view, name='export_json'),
    path('export/zip/', views.export_zip_view, name='export_zip'),
]
```

- [ ] **Step 2: Update `config/urls.py`**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analysis.urls')),
    path('auth/', include('accounts.urls')),
    path('dashboard/', include('billing.urls')),
    path('audit/', include('audit.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
```

- [ ] **Step 3: Verify server starts**

```
C:\Python313\python.exe manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```
git add audit/urls.py config/urls.py
git commit -m "feat(audit): add audit URL routing"
```

---

## Task 6: Create audit templates

**Files:**
- Create: `templates/audit/analysis_log.html`
- Create: `templates/audit/analysis_log_detail.html`
- Create: `templates/audit/audit_log.html`
- Create: `templates/audit/access_denied.html`

- [ ] **Step 1: Create `templates/audit/analysis_log.html`**

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}Tahlil loglari{% endblock %}

{% block extra_style %}
  main { flex: 1; padding-block: 2rem 3rem; }
  .page-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.75rem; }
  .page-header h1 { font-size: 1.6rem; font-weight: 800; letter-spacing: -.03em; background: linear-gradient(90deg, var(--fg-primary), var(--primary-light)); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .export-btns { display: flex; gap: .5rem; flex-wrap: wrap; }
  .btn-export { padding: .5rem 1rem; border-radius: var(--radius); font-size: .8rem; font-weight: 600; cursor: pointer; border: 1px solid var(--border-color); background: transparent; color: var(--fg-secondary); transition: all .2s; display: inline-flex; align-items: center; gap: .4rem; }
  .btn-export:hover { background: var(--bg-hover); border-color: var(--primary-light); color: var(--primary-light); }
  .btn-export-zip { background: rgba(0,180,216,.1); border-color: var(--primary-light); color: var(--primary-light); }
  .stats-strip { display: grid; grid-template-columns: repeat(2,1fr); gap: .75rem; margin-bottom: 1.75rem; }
  @media(min-width:640px){ .stats-strip { grid-template-columns: repeat(4,1fr); } }
  .stat-pill { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius); padding: .875rem 1rem; text-align: center; }
  .stat-pill .val { font-size: 1.5rem; font-weight: 800; color: var(--primary-light); font-family: var(--mono); }
  .stat-pill .lbl { font-size: .7rem; color: var(--fg-muted); text-transform: uppercase; letter-spacing: .05em; margin-top: .2rem; }
  .stat-pill.flagged .val { color: #ef5350; }
  .filter-bar { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius); padding: 1rem 1.25rem; margin-bottom: 1.5rem; display: flex; flex-wrap: wrap; gap: .75rem; align-items: flex-end; }
  .filter-group { display: flex; flex-direction: column; gap: .3rem; }
  .filter-group label { font-size: .72rem; font-weight: 600; color: var(--fg-muted); text-transform: uppercase; letter-spacing: .05em; }
  .filter-input, .filter-select { padding: .5rem .75rem; background: var(--bg-dark); border: 1px solid var(--border-color); border-radius: calc(var(--radius) - 4px); color: var(--fg-primary); font-size: .85rem; font-family: var(--font); outline: none; }
  .filter-input:focus, .filter-select:focus { border-color: var(--primary-light); }
  .filter-select option { background: var(--bg-card); }
  .btn-filter { padding: .5rem 1.25rem; background: linear-gradient(135deg, var(--primary), var(--primary-light)); color: #fff; border: none; border-radius: calc(var(--radius) - 4px); font-weight: 600; font-size: .85rem; cursor: pointer; }
  .table-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius); overflow: hidden; }
  .htable { width: 100%; border-collapse: collapse; }
  .htable th { padding: .75rem 1rem; font-size: .68rem; font-weight: 600; color: var(--fg-muted); text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid var(--border-color); text-align: left; }
  .htable td { padding: .75rem 1rem; font-size: .82rem; border-bottom: 1px solid var(--border-color); color: var(--fg-secondary); }
  .htable tr:last-child td { border-bottom: none; }
  .htable tr:hover td { background: var(--bg-hover); }
  .htable tr.flagged td { background: rgba(244,67,54,.04); }
  .htable tr.flagged:hover td { background: rgba(244,67,54,.08); }
  .badge { display: inline-block; padding: .2rem .55rem; border-radius: 20px; font-size: .68rem; font-weight: 600; border: 1px solid; }
  .badge-ok { background: rgba(76,175,80,.15); color: #81c784; border-color: rgba(76,175,80,.3); }
  .badge-danger { background: rgba(244,67,54,.15); color: #ef5350; border-color: rgba(244,67,54,.3); }
  .badge-muted { background: var(--bg-hover); color: var(--fg-muted); border-color: var(--border-color); }
  .badge-flag { background: rgba(244,67,54,.15); color: #ef5350; border-color: rgba(244,67,54,.3); }
  .view-link { color: var(--primary-light); font-weight: 500; }
  .view-link:hover { text-decoration: underline; }
  .pagination { display: flex; align-items: center; justify-content: center; gap: .5rem; padding: 1rem; flex-wrap: wrap; }
  .page-btn { padding: .4rem .75rem; border: 1px solid var(--border-color); border-radius: calc(var(--radius) - 4px); font-size: .82rem; color: var(--fg-secondary); background: transparent; cursor: pointer; transition: all .2s; }
  .page-btn:hover, .page-btn.active { background: var(--primary); border-color: var(--primary); color: #fff; }
{% endblock %}

{% block content %}
<main>
  <div class="container">

    <div class="page-header">
      <div>
        <h1>Tahlil loglari</h1>
        <p style="color:var(--fg-muted);font-size:.85rem;margin-top:.25rem">AI tahlillar tarixi va shifokor xulosalari</p>
      </div>
      <div class="export-btns">
        <a href="{% url 'export_json' %}?format=json"><button class="btn-export">⬇ JSON</button></a>
        <a href="{% url 'export_json' %}?format=csv"><button class="btn-export">⬇ CSV</button></a>
        <a href="{% url 'export_zip' %}"><button class="btn-export btn-export-zip">📦 ZIP arxiv</button></a>
      </div>
    </div>

    {% if user.is_superuser %}
    <div class="stats-strip">
      <div class="stat-pill"><div class="val">{{ stats.total }}</div><div class="lbl">Jami tahlillar</div></div>
      <div class="stat-pill flagged"><div class="val">{{ stats.flagged }}</div><div class="lbl">Flagged</div></div>
      <div class="stat-pill"><div class="val">{{ stats.avg_confidence }}%</div><div class="lbl">O'rtacha aniqlik</div></div>
      <div class="stat-pill"><div class="val">{{ stats.this_month }}</div><div class="lbl">Bu oy</div></div>
    </div>
    {% endif %}

    <form method="get" class="filter-bar">
      <div class="filter-group">
        <label>Model turi</label>
        <select name="model_type" class="filter-select">
          <option value="">Hammasi</option>
          {% for val, label in model_types %}
            <option value="{{ val }}" {% if filters.model_type == val %}selected{% endif %}>{{ label }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="filter-group">
        <label>Natija</label>
        <select name="verdict" class="filter-select">
          <option value="">Hammasi</option>
          <option value="flagged" {% if filters.verdict == 'flagged' %}selected{% endif %}>🔴 Flagged</option>
          <option value="confirmed" {% if filters.verdict == 'confirmed' %}selected{% endif %}>✓ Tasdiqlangan</option>
          <option value="unreviewed" {% if filters.verdict == 'unreviewed' %}selected{% endif %}>— Ko'rilmagan</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Dan</label>
        <input type="date" name="date_from" class="filter-input" value="{{ filters.date_from }}">
      </div>
      <div class="filter-group">
        <label>Gacha</label>
        <input type="date" name="date_to" class="filter-input" value="{{ filters.date_to }}">
      </div>
      <button type="submit" class="btn-filter">Qidirish</button>
      {% if filters.model_type or filters.verdict or filters.date_from or filters.date_to %}
        <a href="{% url 'analysis_log' %}" style="font-size:.82rem;color:var(--fg-muted);align-self:center">✕ Tozalash</a>
      {% endif %}
    </form>

    <div class="table-card">
      <div style="overflow-x:auto">
        <table class="htable">
          <thead>
            <tr>
              <th>Sana</th>
              <th>Model</th>
              <th>AI natija</th>
              <th>Ishonch</th>
              <th>Shifokor</th>
              <th>Flag</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {% for log in logs %}
            <tr class="{% if log.flagged_for_training %}flagged{% endif %}">
              <td style="font-family:var(--mono);font-size:.75rem">{{ log.created_at|date:"d.m.Y H:i" }}</td>
              <td>{{ log.analysis.get_model_type_display }}</td>
              <td>
                {% if log.error_type %}
                  <span class="badge badge-danger">{{ log.get_error_type_display }}</span>
                {% else %}
                  {{ log.ai_diagnosis|default:"—" }}
                {% endif %}
              </td>
              <td style="font-family:var(--mono)">
                {% if log.ai_confidence %}{{ log.ai_confidence|floatformat:1 }}%{% else %}—{% endif %}
              </td>
              <td>
                {% if log.doctor_verdict is True %}
                  <span class="badge badge-ok">✓ Tasdiqladi</span>
                {% elif log.doctor_verdict is False %}
                  <span class="badge badge-danger">✗ Xato dedi</span>
                {% else %}
                  <span class="badge badge-muted">Ko'rilmagan</span>
                {% endif %}
              </td>
              <td>
                {% if log.flagged_for_training %}
                  <span class="badge badge-flag">🔴 Training</span>
                {% else %}—{% endif %}
              </td>
              <td><a href="{% url 'analysis_log_detail' log.pk %}" class="view-link">Batafsil</a></td>
            </tr>
            {% empty %}
            <tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--fg-muted)">Log yozuvlari topilmadi</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      {% if logs.has_other_pages %}
      <div class="pagination">
        {% if logs.has_previous %}
          <a href="?page={{ logs.previous_page_number }}&model_type={{ filters.model_type }}&verdict={{ filters.verdict }}&date_from={{ filters.date_from }}&date_to={{ filters.date_to }}"><button class="page-btn">← Oldingi</button></a>
        {% endif %}
        <span style="font-size:.82rem;color:var(--fg-muted)">{{ logs.number }} / {{ logs.paginator.num_pages }}</span>
        {% if logs.has_next %}
          <a href="?page={{ logs.next_page_number }}&model_type={{ filters.model_type }}&verdict={{ filters.verdict }}&date_from={{ filters.date_from }}&date_to={{ filters.date_to }}"><button class="page-btn">Keyingi →</button></a>
        {% endif %}
      </div>
      {% endif %}
    </div>

  </div>
</main>
{% endblock %}
```

- [ ] **Step 2: Create `templates/audit/analysis_log_detail.html`**

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}Log #{{ log.pk }}{% endblock %}

{% block extra_style %}
  main { flex: 1; padding-block: 1.5rem 3rem; }
  .breadcrumb { display: flex; align-items: center; gap: .5rem; font-size: .85rem; color: var(--fg-muted); margin-bottom: 1.5rem; }
  .breadcrumb a { color: var(--primary-light); }
  .detail-grid { display: grid; gap: 1.5rem; }
  @media(min-width:900px){ .detail-grid { grid-template-columns: 1fr 1fr; } }
  .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius); padding: 1.5rem; }
  .card-title { font-size: 1rem; font-weight: 700; margin-bottom: 1.25rem; display: flex; align-items: center; gap: .5rem; color: var(--fg-primary); }
  .card-title svg { color: var(--primary-light); width: 1.1rem; height: 1.1rem; }
  .img-wrap { border-radius: calc(var(--radius) - 4px); overflow: hidden; background: #000; }
  .img-wrap img { width: 100%; max-height: 320px; object-fit: contain; display: block; }
  .info-row { display: flex; justify-content: space-between; padding: .55rem 0; border-bottom: 1px solid var(--border-color); font-size: .85rem; }
  .info-row:last-child { border-bottom: none; }
  .info-label { color: var(--fg-muted); }
  .info-val { font-weight: 600; color: var(--fg-primary); }
  .badge { display: inline-block; padding: .2rem .55rem; border-radius: 20px; font-size: .72rem; font-weight: 600; border: 1px solid; }
  .badge-ok { background: rgba(76,175,80,.15); color: #81c784; border-color: rgba(76,175,80,.3); }
  .badge-danger { background: rgba(244,67,54,.15); color: #ef5350; border-color: rgba(244,67,54,.3); }
  .badge-flag { background: rgba(244,67,54,.15); color: #ef5350; border-color: rgba(244,67,54,.3); }
  .badge-muted { background: var(--bg-hover); color: var(--fg-muted); border-color: var(--border-color); }
  .json-collapsible summary { cursor: pointer; font-size: .78rem; color: var(--primary-light); margin-bottom: .5rem; font-weight: 600; }
  .json-collapsible pre { background: var(--bg-dark); border: 1px solid var(--border-color); border-radius: calc(var(--radius) - 4px); padding: .75rem; font-size: .72rem; overflow-x: auto; color: var(--fg-secondary); max-height: 200px; }
  .timeline { margin-top: 1.5rem; }
  .timeline-title { font-size: .9rem; font-weight: 700; color: var(--fg-primary); margin-bottom: 1rem; }
  .tl-item { display: flex; gap: .75rem; padding: .6rem 0; border-bottom: 1px solid var(--border-color); font-size: .8rem; }
  .tl-item:last-child { border-bottom: none; }
  .tl-time { color: var(--fg-muted); font-family: var(--mono); font-size: .72rem; white-space: nowrap; min-width: 120px; }
  .tl-action { font-weight: 600; color: var(--fg-secondary); }
  .tl-user { color: var(--primary-light); }
{% endblock %}

{% block content %}
<main>
  <div class="container">
    <div class="breadcrumb">
      <a href="{% url 'analysis_log' %}">Tahlil loglari</a>
      <span>/</span>
      <span>Log #{{ log.pk }}</span>
    </div>

    <div class="detail-grid">

      <!-- Left: images -->
      <div class="card">
        <div class="card-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5" fill="currentColor"/><polyline points="21 15 16 10 5 21"/></svg>
          Tasvir
        </div>
        {% if log.analysis.image %}
          <div class="img-wrap" style="margin-bottom:1rem"><img src="{{ log.analysis.image.url }}" alt="X-ray"></div>
        {% endif %}
        {% if log.analysis.result.gradcam_image %}
          <div class="img-wrap"><img src="{{ log.analysis.result.gradcam_image.url }}" alt="Grad-CAM"></div>
          <p style="font-size:.72rem;color:var(--fg-muted);margin-top:.4rem">Grad-CAM vizualizatsiya</p>
        {% endif %}
      </div>

      <!-- Right: AI output + doctor verdict -->
      <div>
        <div class="card" style="margin-bottom:1.25rem">
          <div class="card-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            AI natija
          </div>
          <div class="info-row"><span class="info-label">Model</span><span class="info-val">{{ log.analysis.get_model_type_display }}</span></div>
          <div class="info-row"><span class="info-label">Tashxis</span><span class="info-val">{{ log.ai_diagnosis|default:"—" }}</span></div>
          <div class="info-row"><span class="info-label">Ishonch</span><span class="info-val">{{ log.ai_confidence|floatformat:1 }}%</span></div>
          {% if log.error_type %}
          <div class="info-row"><span class="info-label">Xato turi</span><span class="info-val"><span class="badge badge-danger">{{ log.get_error_type_display }}</span></span></div>
          <div class="info-row"><span class="info-label">Xato tafsiloti</span><span class="info-val" style="font-size:.78rem">{{ log.error_detail }}</span></div>
          {% endif %}
          <div class="info-row"><span class="info-label">Muassasa</span><span class="info-val">{{ log.institution|default:"—" }}</span></div>
          <div class="info-row"><span class="info-label">Sana</span><span class="info-val">{{ log.created_at|date:"d.m.Y H:i" }}</span></div>

          <details class="json-collapsible" style="margin-top:1rem">
            <summary>Raw AI output ko'rish</summary>
            <pre>{{ log.ai_raw_output|pprint }}</pre>
          </details>
        </div>

        <div class="card">
          <div class="card-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/></svg>
            Shifokor xulosasi
          </div>
          <div class="info-row">
            <span class="info-label">Xulosa</span>
            <span class="info-val">
              {% if log.doctor_verdict is True %}<span class="badge badge-ok">✓ Tasdiqladi</span>
              {% elif log.doctor_verdict is False %}<span class="badge badge-danger">✗ Xato dedi</span>
              {% else %}<span class="badge badge-muted">Ko'rilmagan</span>{% endif %}
            </span>
          </div>
          {% if log.doctor_note %}
          <div class="info-row"><span class="info-label">Izoh</span><span class="info-val" style="font-size:.82rem">{{ log.doctor_note }}</span></div>
          {% endif %}
          <div class="info-row">
            <span class="info-label">Training uchun</span>
            <span class="info-val">{% if log.flagged_for_training %}<span class="badge badge-flag">🔴 Flagged</span>{% else %}—{% endif %}</span>
          </div>
        </div>
      </div>

    </div>

    {% if audit_events %}
    <div class="card timeline" style="margin-top:1.5rem">
      <div class="timeline-title">Hodisalar jadvali</div>
      {% for event in audit_events %}
      <div class="tl-item">
        <span class="tl-time">{{ event.timestamp|date:"d.m.Y H:i" }}</span>
        <span class="tl-action">{{ event.get_action_display }}</span>
        <span class="tl-user">{{ event.user.get_full_name|default:event.user.username }}</span>
      </div>
      {% endfor %}
    </div>
    {% endif %}

  </div>
</main>
{% endblock %}
```

- [ ] **Step 3: Create `templates/audit/audit_log.html`**

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}Audit log{% endblock %}

{% block extra_style %}
  main { flex: 1; padding-block: 2rem 3rem; }
  .page-header { margin-bottom: 1.75rem; }
  .page-header h1 { font-size: 1.6rem; font-weight: 800; letter-spacing: -.03em; background: linear-gradient(90deg, var(--fg-primary), var(--primary-light)); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .filter-bar { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius); padding: 1rem 1.25rem; margin-bottom: 1.5rem; display: flex; flex-wrap: wrap; gap: .75rem; align-items: flex-end; }
  .filter-group { display: flex; flex-direction: column; gap: .3rem; }
  .filter-group label { font-size: .72rem; font-weight: 600; color: var(--fg-muted); text-transform: uppercase; letter-spacing: .05em; }
  .filter-input, .filter-select { padding: .5rem .75rem; background: var(--bg-dark); border: 1px solid var(--border-color); border-radius: calc(var(--radius) - 4px); color: var(--fg-primary); font-size: .85rem; font-family: var(--font); outline: none; }
  .filter-input:focus, .filter-select:focus { border-color: var(--primary-light); }
  .filter-select option { background: var(--bg-card); }
  .btn-filter { padding: .5rem 1.25rem; background: linear-gradient(135deg, var(--primary), var(--primary-light)); color: #fff; border: none; border-radius: calc(var(--radius) - 4px); font-weight: 600; font-size: .85rem; cursor: pointer; }
  .table-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius); overflow: hidden; }
  .htable { width: 100%; border-collapse: collapse; }
  .htable th { padding: .75rem 1rem; font-size: .68rem; font-weight: 600; color: var(--fg-muted); text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid var(--border-color); text-align: left; }
  .htable td { padding: .75rem 1rem; font-size: .82rem; border-bottom: 1px solid var(--border-color); color: var(--fg-secondary); }
  .htable tr:last-child td { border-bottom: none; }
  .htable tr:hover td { background: var(--bg-hover); }
  .badge { display: inline-block; padding: .2rem .55rem; border-radius: 20px; font-size: .68rem; font-weight: 600; border: 1px solid var(--border-color); background: var(--bg-hover); color: var(--fg-muted); }
  .pagination { display: flex; align-items: center; justify-content: center; gap: .5rem; padding: 1rem; }
  .page-btn { padding: .4rem .75rem; border: 1px solid var(--border-color); border-radius: calc(var(--radius) - 4px); font-size: .82rem; color: var(--fg-secondary); background: transparent; cursor: pointer; transition: all .2s; }
  .page-btn:hover { background: var(--primary); border-color: var(--primary); color: #fff; }
  .json-collapsible summary { cursor: pointer; font-size: .75rem; color: var(--primary-light); }
  .json-collapsible pre { background: var(--bg-dark); padding: .5rem; border-radius: 4px; font-size: .7rem; max-height: 120px; overflow: auto; margin-top: .25rem; }
{% endblock %}

{% block content %}
<main>
  <div class="container">
    <div class="page-header">
      <h1>Xavfsizlik audit logi</h1>
      <p style="color:var(--fg-muted);font-size:.85rem;margin-top:.25rem">Tizimga kirish, chiqish va to'lov hodisalari</p>
    </div>

    <form method="get" class="filter-bar">
      <div class="filter-group">
        <label>Foydalanuvchi</label>
        <input type="text" name="username" class="filter-input" placeholder="username" value="{{ filters.username }}">
      </div>
      <div class="filter-group">
        <label>Harakat</label>
        <select name="action" class="filter-select">
          <option value="">Hammasi</option>
          {% for val, label in actions %}
            <option value="{{ val }}" {% if filters.action == val %}selected{% endif %}>{{ label }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="filter-group">
        <label>Dan</label>
        <input type="date" name="date_from" class="filter-input" value="{{ filters.date_from }}">
      </div>
      <div class="filter-group">
        <label>Gacha</label>
        <input type="date" name="date_to" class="filter-input" value="{{ filters.date_to }}">
      </div>
      <button type="submit" class="btn-filter">Qidirish</button>
    </form>

    <div class="table-card">
      <div style="overflow-x:auto">
        <table class="htable">
          <thead>
            <tr>
              <th>Vaqt</th>
              <th>Foydalanuvchi</th>
              <th>Harakat</th>
              <th>IP manzil</th>
              <th>Ma'lumot</th>
            </tr>
          </thead>
          <tbody>
            {% for log in logs %}
            <tr>
              <td style="font-family:var(--mono);font-size:.75rem;white-space:nowrap">{{ log.timestamp|date:"d.m.Y H:i" }}</td>
              <td>{{ log.user.get_full_name|default:log.user.username|default:"—" }}</td>
              <td><span class="badge">{{ log.get_action_display }}</span></td>
              <td style="font-family:var(--mono);font-size:.75rem">{{ log.ip_address|default:"—" }}</td>
              <td>
                {% if log.data %}
                <details class="json-collapsible">
                  <summary>ko'rish</summary>
                  <pre>{{ log.data|pprint }}</pre>
                </details>
                {% else %}—{% endif %}
              </td>
            </tr>
            {% empty %}
            <tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--fg-muted)">Yozuvlar topilmadi</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% if logs.has_other_pages %}
      <div class="pagination">
        {% if logs.has_previous %}<a href="?page={{ logs.previous_page_number }}&username={{ filters.username }}&action={{ filters.action }}"><button class="page-btn">← Oldingi</button></a>{% endif %}
        <span style="font-size:.82rem;color:var(--fg-muted)">{{ logs.number }} / {{ logs.paginator.num_pages }}</span>
        {% if logs.has_next %}<a href="?page={{ logs.next_page_number }}&username={{ filters.username }}&action={{ filters.action }}"><button class="page-btn">Keyingi →</button></a>{% endif %}
      </div>
      {% endif %}
    </div>
  </div>
</main>
{% endblock %}
```

- [ ] **Step 4: Create `templates/audit/access_denied.html`**

```django
{% extends 'base.html' %}
{% block title %}Kirish taqiqlangan{% endblock %}
{% block content %}
<main style="flex:1;display:flex;align-items:center;justify-content:center">
  <div style="text-align:center;padding:3rem">
    <div style="font-size:3rem;margin-bottom:1rem">🔒</div>
    <h2 style="font-size:1.5rem;font-weight:700;margin-bottom:.5rem">Kirish taqiqlangan</h2>
    <p style="color:var(--fg-muted)">Bu sahifaga kirish uchun yetarli huquq yo'q.</p>
    <a href="{% url 'dashboard' %}" style="display:inline-block;margin-top:1.5rem;padding:.65rem 1.5rem;background:linear-gradient(135deg,var(--primary),var(--primary-light));color:#fff;border-radius:var(--radius);font-weight:600">Kabinetga qaytish</a>
  </div>
</main>
{% endblock %}
```

- [ ] **Step 5: Commit**

```
git add templates/audit/
git commit -m "feat(audit): add analysis_log, audit_log, detail, and access_denied templates"
```

---

## Task 7: Update `dashboard.html` — flagged stat card

**Files:**
- Modify: `templates/dashboard/dashboard.html`

- [ ] **Step 1: Add flagged card after stats grid**

Find the closing `</div>` of `.stats-grid` block and add this snippet immediately after it:

```django
      {% if user.is_superuser or user.is_university %}
      <a href="{% url 'analysis_log' %}?verdict=flagged" style="text-decoration:none">
        <div class="section-card" style="background:rgba(244,67,54,.06);border-color:rgba(244,67,54,.25);padding:1rem 1.5rem;display:flex;align-items:center;justify-content:space-between;cursor:pointer;transition:all .2s;margin-bottom:2rem">
          <div style="display:flex;align-items:center;gap:.75rem">
            <div style="width:2.5rem;height:2.5rem;border-radius:10px;background:rgba(244,67,54,.15);display:flex;align-items:center;justify-content:center;font-size:1.1rem">🔴</div>
            <div>
              <div style="font-weight:700;color:#ef5350">Flagged tahlillar</div>
              <div style="font-size:.78rem;color:var(--fg-muted)">Shifokor xato deb belgilagan AI natijalari</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:.5rem;color:var(--primary-light);font-weight:600;font-size:.85rem">
            Ko'rish →
          </div>
        </div>
      </a>
      {% endif %}
```

- [ ] **Step 2: Add audit nav links in dashboard header** (optional — add links to navbar section)

In `base.html`, after the `Kabinet` nav button for authenticated users, add:

```django
      {% if user.is_superuser or user.is_university %}
        <a href="{% url 'analysis_log' %}">
          <button class="btn btn-ghost" type="button">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            <span class="nav-label">Audit</span>
          </button>
        </a>
      {% endif %}
```

- [ ] **Step 3: Commit**

```
git add templates/dashboard/dashboard.html templates/base.html
git commit -m "feat(dashboard): add flagged analyses card and audit nav link for university/superuser"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run system check**

```
C:\Python313\python.exe manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 2: Start server and verify routes**

```
C:\Python313\python.exe manage.py runserver 8002
```

Open in browser:
- `http://127.0.0.1:8002/audit/analyses/` — should show analysis log table (login first)
- `http://127.0.0.1:8002/audit/` — should show security audit log (superuser only)
- `http://127.0.0.1:8002/dashboard/` — should show flagged card for superuser

- [ ] **Step 3: Final commit**

```
git add -A
git commit -m "feat(audit): complete AnalysisLog system with views, templates, and export"
git push origin Oybek
```
