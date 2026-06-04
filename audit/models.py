from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'login', 'Tizimga kirish'
        LOGOUT = 'logout', 'Tizimdan chiqish'
        REGISTER = 'register', "Ro'yxatdan o'tish"
        UPLOAD = 'upload', 'Rasm yuklash'
        ANALYZE = 'analyze', 'Tahlil boshlash'
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
