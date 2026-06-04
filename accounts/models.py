from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Talaba'
        DOCTOR = 'doctor', 'Shifokor'
        UNIVERSITY = 'university', 'Oliygoh'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=13, unique=True, null=True, blank=True)
    institution = models.CharField(max_length=255, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_university(self):
        return self.role == self.Role.UNIVERSITY
