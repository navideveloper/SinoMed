from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'get_full_name', 'role', 'phone', 'institution', 'balance', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'phone', 'institution')
    fieldsets = UserAdmin.fieldsets + (
        ('SinoMed', {'fields': ('role', 'phone', 'institution', 'balance', 'avatar')}),
    )
