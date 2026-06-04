from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.org_dashboard, name='org_dashboard'),
    path('users/<int:pk>/approve/', views.approve_user, name='approve_user'),
    path('users/<int:pk>/reject/', views.reject_user, name='reject_user'),
]
