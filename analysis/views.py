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

def _save_heatmap(result: AnalysisResult, b64_data: str) -> None:
    """Decode base64 heatmap and save to gradcam_image field."""
    if not b64_data:
        return
    try:
        raw = b64_data.split(',', 1)[-1]
        img_bytes = base64.b64decode(raw)
        result.gradcam_image.save(
            f'heatmap_{result.analysis_id}.png',
            ContentFile(img_bytes),
            save=True,
        )
    except Exception:
        pass  # heatmap optional


def _draw_prostate_detections(result: AnalysisResult, detections: list) -> None:
    """
    Prostate detections uchun bounding box larni original rasm ustiga chizib
    gradcam_image ga saqlaydi.
    box format: [x1, y1, x2, y2]
    """
    if not detections:
        return
    try:
        import io
        from PIL import Image, ImageDraw

        img = Image.open(result.analysis.image.path).convert('RGB')
        draw = ImageDraw.Draw(img)

        # Grade bo'yicha rang
        grade_colors = {
            'grade3': (0, 180, 216),    # ko'k
            'grade4': (255, 152,   0),  # sariq
            'grade5': (244,  67,  54),  # qizil
        }
        default_color = (0, 212, 255)

        for det in detections:
            box = det.get('box', [])
            if len(box) != 4:
                continue
            x1, y1, x2, y2 = [float(v) for v in box]
            label       = det.get('label', '')
            conf_pct    = det.get('confidence_percent', 0)

            # Rangni label dan aniqlash
            color = default_color
            for grade_key, grade_color in grade_colors.items():
                if grade_key in label.lower():
                    color = grade_color
                    break

            line_width = max(2, int(min(img.width, img.height) * 0.004))

            # Bounding box
            draw.rectangle([x1, y1, x2, y2], outline=color, width=line_width)

            # Label background
            text        = f"{label} {conf_pct}%"
            font_size   = max(12, int(min(img.width, img.height) * 0.025))
            label_h     = font_size + 6
            label_y0    = max(0, y1 - label_h)
            draw.rectangle(
                [x1, label_y0, x1 + len(text) * font_size * 0.6 + 8, y1],
                fill=color,
            )
            draw.text((x1 + 4, label_y0 + 2), text, fill=(255, 255, 255))

        buf = io.BytesIO()
        img.save(buf, format='PNG', quality=92)
        buf.seek(0)
        result.gradcam_image.save(
            f'prostate_{result.analysis_id}.png',
            ContentFile(buf.read()),
            save=True,
        )
    except Exception:
        pass  # drawing optional — asosiy natijaga ta'sir qilmaydi


def _call_ai(model_type: str, image_path: str, extra_data: dict = None) -> dict:
    """
    AI servisiga multipart/form-data POST jo'natadi.
    Prostate: 'file' parametri + X-API-Key header.
    Pneumonia/BoneAge: 'image' parametri.
    """
    url = settings.AI_ENDPOINTS.get(model_type, '')
    if not url:
        raise ValueError(f"'{model_type}' uchun AI endpoint sozlanmagan")

    # Prostate: parametr nomi 'file', qolganlarida 'image'
    file_param = 'file' if model_type == 'prostate' else 'image'

    headers = {}
    if model_type == 'prostate':
        api_key = getattr(settings, 'PROSTATE_API_KEY', '')
        if api_key:
            headers['X-API-Key'] = api_key

    with open(image_path, 'rb') as f:
        import os as _os
        filename = _os.path.basename(image_path)
        resp = http_client.post(
            url,
            files={file_param: (filename, f, 'image/jpeg')},
            data=extra_data or {},
            headers=headers,
            timeout=settings.AI_SERVICE_TIMEOUT,
        )

    resp.raise_for_status()
    return resp.json()


def _parse_ai_response(model_type: str, ai_resp: dict) -> dict:
    """
    Har model uchun AI javobini bir xil ichki formatga o'tkazadi.
    Qaytaradi: {diagnosis, diagnosis_type, confidence, note, heatmap_b64}
    """
    if model_type == 'pneumonia':
        # {"status": "PNEVMONIYA", "probability": 98.45, "heatmap_image": "..."}
        raw_status = ai_resp.get('status', "NOMA'LUM")
        s = raw_status.upper()
        if s in ('NORMAL', 'SOGLOM', "SOG'LOM", 'HEALTHY'):
            dtype = AnalysisResult.DiagnosisType.NORMAL
        elif s in ('PNEVMONIYA', 'PNEUMONIA'):
            dtype = AnalysisResult.DiagnosisType.DANGER
        else:
            dtype = AnalysisResult.DiagnosisType.WARNING
        return {
            'diagnosis':   raw_status,
            'dtype':       dtype,
            'confidence':  float(ai_resp.get('probability', 0.0)),
            'note':        '',
            'heatmap_b64': ai_resp.get('heatmap_image', ''),
        }

    elif model_type == 'bone_age':
        # {"formatlangan_yosh": "10 yosh, 4 oy", "jami_oylik": 124,
        #  "jinsi": "Ayol", "yosh_yil": 10.3}
        formatlangan = ai_resp.get('formatlangan_yosh', "Noma'lum")
        jinsi        = ai_resp.get('jinsi', '')
        jami_oylik   = ai_resp.get('jami_oylik', '')
        yosh_yil     = float(ai_resp.get('yosh_yil', 0.0))
        note = f"Jinsi: {jinsi}" + (f" | Jami oylik: {jami_oylik}" if jami_oylik else '')
        return {
            'diagnosis':   formatlangan,
            'dtype':       AnalysisResult.DiagnosisType.NORMAL,  # yoshni aniqlash kasallik emas
            'confidence':  100.0,   # regression model — aniq qiymat
            'note':        note,
            'heatmap_b64': '',
            'yosh_yil':    yosh_yil,
        }

    elif model_type == 'prostate':
        # OpenAPI spec: {disease_probability_percent, conclusion, detections_count, detections}
        probability   = int(ai_resp.get('disease_probability_percent', 0))
        conclusion    = ai_resp.get('conclusion', "Noma'lum")
        det_count     = ai_resp.get('detections_count', 0)
        detections    = ai_resp.get('detections', [])

        if probability >= 70:
            dtype = AnalysisResult.DiagnosisType.DANGER
        elif probability >= 40:
            dtype = AnalysisResult.DiagnosisType.WARNING
        else:
            dtype = AnalysisResult.DiagnosisType.NORMAL

        # Aniqlangan sohalar ro'yxati (label + confidence)
        det_text = ''
        if detections:
            parts = [f"{d['label']} ({d['confidence_percent']}%)" for d in detections[:5]]
            det_text = ' | '.join(parts)

        note = conclusion
        if det_count:
            note += f"\n{det_count} ta soha aniqlandi" + (f": {det_text}" if det_text else '')

        return {
            'diagnosis':   conclusion,
            'dtype':       dtype,
            'confidence':  float(probability),
            'note':        note,
            'heatmap_b64': '',
        }

    # Fallback
    return {
        'diagnosis':   str(ai_resp),
        'dtype':       AnalysisResult.DiagnosisType.WARNING,
        'confidence':  0.0,
        'note':        '',
        'heatmap_b64': '',
    }


def _result_to_dict(result: AnalysisResult) -> dict:
    d = {
        'analysis_id':    result.analysis_id,
        'diagnosis':      result.diagnosis,
        'diagnosis_type': result.diagnosis_type,
        'confidence':     result.confidence,
        'note':           result.note,
        'gradcam_url':    result.gradcam_image.url if result.gradcam_image else None,
        'status':         'completed',
        'model_type':     result.analysis.model_type,
    }
    # Bone age: jami_oylik ni JS comparison uchun qaytaramiz
    if result.analysis.model_type == 'bone_age' and result.raw_output:
        d['jami_oylik'] = result.raw_output.get('jami_oylik')
        d['jinsi']      = result.raw_output.get('jinsi', '')
    return d


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
        is_female   = data.get('is_female', False)   # bone_age uchun
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
        # Bone age uchun is_female parametri qo'shiladi
        extra = {}
        if analysis.model_type == 'bone_age' and is_female:
            extra['is_female'] = 'true'

        ai_resp = _call_ai(analysis.model_type, analysis.image.path, extra)

        # AI xato qaytargan bo'lsa
        if 'error' in ai_resp:
            raise ValueError(ai_resp['error'])

        # Har model uchun javobni parse qilamiz
        parsed = _parse_ai_response(analysis.model_type, ai_resp)

        result = AnalysisResult.objects.create(
            analysis=analysis,
            diagnosis=parsed['diagnosis'],
            diagnosis_type=parsed['dtype'],
            confidence=parsed['confidence'],
            note=parsed['note'],
            raw_output=ai_resp,
        )

        # Vizualizatsiya: pnevmoniya → heatmap (base64), prostate → box drawing
        if analysis.model_type == 'prostate':
            _draw_prostate_detections(result, ai_resp.get('detections', []))
        else:
            _save_heatmap(result, parsed['heatmap_b64'])

        analysis.status = Analysis.Status.COMPLETED
        analysis.save(update_fields=['status'])

        AnalysisLog.objects.create(
            analysis=analysis,
            ai_diagnosis=parsed['diagnosis'],
            ai_confidence=parsed['confidence'],
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
    user = request.user
    # Shifokor: o'z muassasasi + org=None (superuser test) tahlillarini ko'ra oladi
    from django.db.models import Q
    if user.is_superuser:
        analysis = get_object_or_404(Analysis, pk=pk)
    elif user.is_doctor and user.organization_id:
        analysis = get_object_or_404(
            Analysis.objects.filter(
                Q(user__organization_id=user.organization_id) |
                Q(user__is_superuser=True)
            ),
            pk=pk
        )
    else:
        analysis = get_object_or_404(Analysis, pk=pk, user=user)

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

    result = getattr(analysis, 'result', None)
    detections = []
    if result and analysis.model_type == 'prostate' and result.raw_output:
        detections = result.raw_output.get('detections', [])

    context = {
        'analysis':   analysis,
        'result':     result,
        'detections': detections,
    }
    return render(request, 'analysis/result.html', context)
