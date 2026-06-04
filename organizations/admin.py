from django.contrib import admin
from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'org_type', 'code', 'is_active', 'created_at']
    list_filter = ['org_type', 'is_active']
    search_fields = ['name', 'code', 'email']
    list_editable = ['is_active']
