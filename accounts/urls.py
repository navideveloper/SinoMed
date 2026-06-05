from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:pk>/', views.user_detail_view, name='user_detail'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('users/<int:pk>/update-balance/', views.user_update_balance, name='user_update_balance'),
    path('users/<int:pk>/change-password/', views.user_change_password, name='user_change_password'),
    # API endpoint for org selection in registration form
    path('api/organizations/', views.api_organizations, name='api_organizations'),
    # SuperAdmin CRUD
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete_view, name='user_delete'),
]
