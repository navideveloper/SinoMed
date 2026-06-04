from django.db import models
from django.conf import settings


class Plan(models.Model):
    class PlanType(models.TextChoices):
        DOCTOR_MONTHLY = 'doctor_monthly', 'Shifokor — Oylik'
        DOCTOR_YEARLY = 'doctor_yearly', 'Shifokor — Yillik'
        UNIVERSITY_YEARLY = 'university_yearly', 'Oliygoh — Yillik litsenziya'

    plan_type = models.CharField(max_length=30, choices=PlanType.choices, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    analyses_limit = models.IntegerField(help_text='0 = cheksiz')
    duration_days = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tarif'
        verbose_name_plural = 'Tariflar'

    def __str__(self):
        return f"{self.get_plan_type_display()} — {self.price:,.0f} so'm"


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        EXPIRED = 'expired', "Muddati o'tgan"
        CANCELLED = 'cancelled', 'Bekor qilingan'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField()
    analyses_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Obuna'
        verbose_name_plural = 'Obunalar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.plan} ({self.status})'

    @property
    def is_currently_active(self):
        from django.utils import timezone
        return self.status == self.Status.ACTIVE and self.end_date >= timezone.now().date()


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        SUCCESS = 'success', 'Muvaffaqiyatli'
        FAILED = 'failed', 'Xato'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.amount:,.0f} so'm ({self.status})"
