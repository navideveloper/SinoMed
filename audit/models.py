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
