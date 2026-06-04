from django.contrib import admin
from .models import Analysis, AnalysisResult


class AnalysisResultInline(admin.StackedInline):
    model = AnalysisResult
    extra = 0


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'model_type', 'status', 'created_at')
    list_filter = ('model_type', 'status', 'created_at')
    search_fields = ('user__username', 'user__first_name')
    inlines = [AnalysisResultInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'analysis', 'diagnosis', 'diagnosis_type', 'confidence', 'doctor_confirmed')
    list_filter = ('diagnosis_type', 'doctor_confirmed')
    search_fields = ('diagnosis', 'analysis__user__username')
