from django.urls import path
from . import views

urlpatterns = [
    path('', views.audit_log_view, name='audit_log'),
    path('analyses/', views.analysis_log_view, name='analysis_log'),
    path('analyses/<int:pk>/', views.analysis_log_detail_view, name='analysis_log_detail'),
    path('export/json/', views.export_json_view, name='export_json'),
    path('export/zip/', views.export_zip_view, name='export_zip'),
]
