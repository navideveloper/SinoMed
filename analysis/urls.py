from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('analyze/', views.upload_analyze, name='upload_analyze'),
    path('analyze/<int:pk>/result/', views.result_detail, name='result_detail'),
    path('api/analyze/', views.api_analyze, name='api_analyze'),
    path('pricing/', views.pricing, name='pricing'),
]
