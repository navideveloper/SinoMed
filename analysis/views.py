import base64
import json

import requests as http_client
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Analysis, AnalysisResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_to_diagnosis_type(status: str) -> str:
    """Map AI `status` string to DiagnosisType choice."""
    s = (status or '').upper()
    if s in ('NORMAL', 'SOGLOM', 'HEALTHY'):
        return AnalysisResult.DiagnosisType.NORMAL
    if s in ('PNEVMONIYA', 'PNEUMONIA', 'SARATON', 'CANCER', 'PROSTATE', 'PATHOLOGY'):
        return AnalysisResult.DiagnosisType.DANGER
    return AnalysisResult.DiagnosisType.WARNING


def _save_heatmap(result: AnalysisResult, b64_data: str) -> None:
    """Decode base64 heatmap and save to gradcam_image field."""
    if not b64_data:
        return
    try:
        # Strip "data:image/png;base64," prefix if present
        raw = b64_data.split(',', 1)[-1]
        img_bytes = base64.b64decode(raw)
        result.gradcam_image.save(
            f'heatmap_{result.analysis_id}.png',
            ContentFile(img_bytes),
            save=True,
        )
    except Exception:
        pass  # heatmap optional — tahlil natijasiga ta'sir qilmaydi


def _call_ai(model_type: str, image_path: str) -> dict:
    """
    AI servisiga multipart/form-data POST jo'natadi.
    Javob: {'status': str, 'probability': float, 'heatmap_image': str|None}
    Xato bo'lsa: {'error': str} yoki exception
    """
    url = settings.AI_ENDPOINTS.get(model_type, '')
    if not url:
        raise ValueError(f"'{model_type}' uchun AI endpoint sozlanmagan")

    with open(image_path, 'rb') as f:
        resp = http_client.post(
            url,
            files={'image': (f.name, f, 'image/jpeg')},
            timeout=settings.AI_SERVICE_TIMEOUT,
        )

    resp.raise_for_status()
    return resp.json()


def _result_to_dict(result: AnalysisResult) -> dict:
    return {
        'analysis_id':    result.analysis_id,
        'diagnosis':      result.diagnosis,
        'diagnosis_type': result.diagnosis_type,
        'confidence':     result.confidence,
        'note':           result.note,
        'gradcam_url':    result.gradcam_image.url if result.gradcam_image else None,
        'status':         'completed',
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def index(request):
    return render(request, 'index.html')


def pricing(request):
    return render(request, 'analysis/pricing.html')


@login_required
def upload_analyze(request):
    if request.method == 'POST':
        model_type = request.POST.get('model_type')
        image = request.FILES.get('image')

        if not image or model_type not in dict(Analysis.ModelType.choices):
            return JsonResponse({'error': "Noto'g'ri ma'lumot"}, status=400)

        analysis = Analysis.objects.create(
            user=request.user,
            model_type=model_type,
            image=image,
            status=Analysis.Status.PENDING,
        )

        from audit.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.UPLOAD,
            analysis=analysis,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return JsonResponse({'analysis_id': analysis.pk, 'status': 'uploaded'})

    return render(request, 'analysis/upload.html', {
        'model_types': Analysis.ModelType.choices,
    })


@login_required
@require_POST
def api_analyze(request):
    """AJAX: rasm AI servisiga yuboriladi, natija qaytariladi."""
    try:
        data = json.loads(request.body)
        analysis_id = data.get('analysis_id')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    analysis = get_object_or_404(Analysis, pk=analysis_id, user=request.user)

    # Allaqachon tahlil qilingan bo'lsa — qayta qaytaramiz
    if hasattr(analysis, 'result'):
        return JsonResponse(_result_to_dict(analysis.result))

    analysis.status = Analysis.Status.PROCESSING
    analysis.save(update_fields=['status'])

    from audit.models import AuditLog, AnalysisLog

    result = None
    error_type = None
    error_detail = ''

    try:
        ai_resp = _call_ai(analysis.model_type, analysis.image.path)

        # AI xato qaytargan bo'lsa
        if 'error' in ai_resp:
            raise ValueError(ai_resp['error'])

        # Javobni parse qilamiz
        raw_status   = ai_resp.get('status', 'NOMA\'LUM')
        probability  = float(ai_resp.get('probability', 0.0))
        heatmap_b64  = ai_resp.get('heatmap_image', '')

        diagnosis_type = _status_to_diagnosis_type(raw_status)

        result = AnalysisResult.objects.create(
            analysis=analysis,
            diagnosis=raw_status,
            diagnosis_type=diagnosis_type,
            confidence=probability,
            note='',
            raw_output=ai_resp,
        )

        # Heatmap ni saqlash
        _save_heatmap(result, heatmap_b64)

        analysis.status = Analysis.Status.COMPLETED
        analysis.save(update_fields=['status'])

        AnalysisLog.objects.create(
            analysis=analysis,
            ai_diagnosis=raw_status,
            ai_confidence=probability,
            ai_raw_output=ai_resp,
            institution=request.user.institution,
        )

    except http_client.Timeout as e:
        error_type   = AnalysisLog.ErrorType.TIMEOUT
        error_detail = str(e)
        analysis.status = Analysis.Status.ERROR
        analysis.save(update_fields=['status'])
        result = AnalysisResult.objects.create(
            analysis=analysis,
            diagnosis="Vaqt tugadi",
            diagnosis_type=AnalysisResult.DiagnosisType.WARNING,
            confidence=0.0,
            note=error_detail,
            raw_output={'error': error_detail},
        )
        AnalysisLog.objects.create(
            analysis=analysis, ai_diagnosis='', ai_confidence=0.0,
            ai_raw_output={'error': error_detail},
            error_type=error_type, error_detail=error_detail,
            institution=request.user.institution,
        )

    except Exception as e:
        error_type   = AnalysisLog.ErrorType.SERVICE_ERROR
        error_detail = str(e)
        analysis.status = Analysis.Status.ERROR
        analysis.save(update_fields=['status'])
        result = AnalysisResult.objects.create(
            analysis=analysis,
            diagnosis="Tahlil qilib bo'lmadi",
            diagnosis_type=AnalysisResult.DiagnosisType.WARNING,
            confidence=0.0,
            note=error_detail,
            raw_output={'error': error_detail},
        )
        AnalysisLog.objects.create(
            analysis=analysis, ai_diagnosis='', ai_confidence=0.0,
            ai_raw_output={'error': error_detail},
            error_type=error_type, error_detail=error_detail,
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
