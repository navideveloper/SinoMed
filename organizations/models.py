from django.db import models


class Organization(models.Model):
    class OrgType(models.TextChoices):
        UNIVERSITY = 'university', "Oliy ta'lim muassasasi"
        HOSPITAL = 'hospital', 'Kasalxona'

    name = models.CharField(max_length=255, verbose_name='Nomi')
    org_type = models.CharField(
        max_length=20, choices=OrgType.choices, verbose_name='Turi'
    )
    code = models.CharField(
        max_length=50, unique=True, verbose_name='Kod',
        help_text='Qisqa identifikator (masalan: TDTU, TOSHMI)'
    )
    address = models.TextField(blank=True, verbose_name='Manzil')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefon')
    email = models.EmailField(blank=True, verbose_name='Email')
    website = models.URLField(blank=True, verbose_name='Veb-sayt')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Muassasa'
        verbose_name_plural = 'Muassasalar'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_org_type_display()})'

    @property
    def pending_count(self):
        return self.members.filter(approval_status='pending').count()

    @property
    def active_member_count(self):
        return self.members.filter(approval_status='approved', is_active=True).count()
