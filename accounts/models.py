from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Talaba'
        DOCTOR = 'doctor', 'Shifokor'
        ORG_ADMIN = 'org_admin', 'Muassasa admini'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', 'Tasdiqlash kutilmoqda'
        APPROVED = 'approved', 'Tasdiqlandi'
        REJECTED = 'rejected', 'Rad etildi'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=13, unique=True, null=True, blank=True)

    # Organization membership
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='members',
        verbose_name='Muassasa'
    )
    # Legacy free-text institution field (kept for backward compat with AnalysisLog)
    institution = models.CharField(max_length=255, blank=True)

    # Registration approval
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,  # superuser-created users auto-approved
        verbose_name='Tasdiqlash holati'
    )
    rejection_reason = models.TextField(blank=True, verbose_name='Rad etish sababi')

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    # ── role helpers ──────────────────────────────────────────────
    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_university(self):
        """Legacy alias — org_admin of a university org, or superuser."""
        return self.role == self.Role.ORG_ADMIN or self.is_superuser

    @property
    def is_org_admin(self):
        return self.role == self.Role.ORG_ADMIN

    # ── approval helpers ─────────────────────────────────────────
    @property
    def is_pending(self):
        return self.approval_status == self.ApprovalStatus.PENDING

    @property
    def is_rejected(self):
        return self.approval_status == self.ApprovalStatus.REJECTED

    @property
    def org_name(self):
        """Convenience: org name or fallback to legacy institution field."""
        if self.organization:
            return self.organization.name
        return self.institution
