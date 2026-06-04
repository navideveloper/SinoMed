from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Analysis, AnalysisResult
import json
import urllib.request
import urllib.error


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
            return JsonResponse({'error': 'Noto\'g\'ri ma\'lumot'}, status=400)

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

    except (urllib.error.URLError, TimeoutError, Exception) as e:
        analysis.status = Analysis.Status.ERROR
        analysis.save(update_fields=['status'])

        result = AnalysisResult.objects.create(
            analysis=analysis,
            diagnosis='Tahlil qilib bo\'lmadi',
            diagnosis_type=AnalysisResult.DiagnosisType.WARNING,
            confidence=0.0,
            note=str(e),
            raw_output={'error': str(e)},
        )

    from audit.models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action=AuditLog.Action.ANALYZE,
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
        from audit.models import AuditLog

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

        return redirect('result_detail', pk=pk)

    context = {
        'analysis': analysis,
        'result': getattr(analysis, 'result', None),
    }
    return render(request, 'analysis/result.html', context)


def _result_to_dict(result):
    return {
        'analysis_id': result.analysis_id,
        'diagnosis': result.diagnosis,
        'diagnosis_type': result.diagnosis_type,
        'confidence': result.confidence,
        'note': result.note,
        'gradcam_url': result.gradcam_image.url if result.gradcam_image else None,
        'status': 'completed',
    }
