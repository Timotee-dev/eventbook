import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import TimeStampedModel

class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        PROVIDER = 'provider', 'Event Provider'
        ADMIN    = 'admin',    'Admin'

    email               = models.EmailField(unique=True)
    role                = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone               = models.CharField(max_length=20, blank=True)
    is_email_verified   = models.BooleanField(default=False)
    is_provider_approved= models.BooleanField(default=False)
    avatar              = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio                 = models.TextField(blank=True)
    company_name        = models.CharField(max_length=150, blank=True)
    city                = models.CharField(max_length=100, blank=True)
    state               = models.CharField(max_length=100, blank=True)
    bank_name           = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=20, blank=True)
    bank_account_name   = models.CharField(max_length=150, blank=True)
    paystack_recipient_code = models.CharField(max_length=100, blank=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    @property
    def is_customer(self): return self.role == self.Role.CUSTOMER
    @property
    def is_provider(self): return self.role == self.Role.PROVIDER
    @property
    def is_admin_role(self): return self.role == self.Role.ADMIN or self.is_superuser

    def __str__(self): return self.email


class EmailToken(TimeStampedModel):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_tokens')
    token      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    purpose    = models.CharField(max_length=20, default='verify')  # verify | reset
    is_used    = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.pk and not self.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            hours = 1 if self.purpose == 'reset' else 24
            self.expires_at = timezone.now() + timedelta(hours=hours)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at
