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
