from django.db import models
from django.conf import settings


class Analysis(models.Model):
    class ModelType(models.TextChoices):
        BONE_AGE = 'bone_age', "Suyak yoshi (Qo'l rentgeni)"
        PROSTATE = 'prostate', 'Prostata saraton'
        PNEUMONIA = 'pneumonia', "O'pka yallig'lanishi"

    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        PROCESSING = 'processing', 'Tahlil qilinmoqda'
        COMPLETED = 'completed', 'Tugallandi'
        ERROR = 'error', 'Xato'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    model_type = models.CharField(max_length=20, choices=ModelType.choices)
    image = models.ImageField(upload_to='xrays/%Y/%m/')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tahlil'
        verbose_name_plural = 'Tahlillar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_model_type_display()} — {self.user} ({self.created_at:%d.%m.%Y})'


class AnalysisResult(models.Model):
    class DiagnosisType(models.TextChoices):
        NORMAL = 'normal', 'Normal'
        WARNING = 'warning', "E'tibor talab"
        DANGER = 'danger', 'Patologiya'

    analysis = models.OneToOneField(Analysis, on_delete=models.CASCADE, related_name='result')
    diagnosis = models.CharField(max_length=255)
    diagnosis_type = models.CharField(max_length=10, choices=DiagnosisType.choices)
    confidence = models.FloatField()
    note = models.TextField(blank=True)
    gradcam_image = models.ImageField(upload_to='gradcam/%Y/%m/', null=True, blank=True)
    raw_output = models.JSONField(default=dict)

    doctor_confirmed = models.BooleanField(null=True, blank=True)
    doctor_note = models.TextField(blank=True)
    doctor_report = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_results'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tahlil natijasi'
        verbose_name_plural = 'Tahlil natijalari'

    def __str__(self):
        return f'{self.diagnosis} ({self.confidence:.1f}%)'
