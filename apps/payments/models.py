import uuid
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.bookings.models import Booking

def gen_pay_ref():
    return 'PAY-' + uuid.uuid4().hex[:16].upper()

class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        SUCCESS   = 'success',   'Success'
        FAILED    = 'failed',    'Failed'
        REFUNDED  = 'refunded',  'Refunded'
        ABANDONED = 'abandoned', 'Abandoned'

    booking           = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    reference         = models.CharField(max_length=100, unique=True, default=gen_pay_ref, editable=False)
    paystack_ref      = models.CharField(max_length=100, blank=True, db_index=True)
    authorization_url = models.URLField(blank=True)
    access_code       = models.CharField(max_length=100, blank=True)
    amount            = models.DecimalField(max_digits=12, decimal_places=2)
    status            = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    channel           = models.CharField(max_length=30, blank=True)
    paid_at           = models.DateTimeField(null=True, blank=True)
    gateway_response  = models.CharField(max_length=255, blank=True)
    webhook_payload   = models.JSONField(null=True, blank=True)

    def __str__(self): return f'{self.reference} {self.status}'


class RevenueSplit(TimeStampedModel):
    payment         = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='split')
    provider        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='splits')
    gross           = models.DecimalField(max_digits=12, decimal_places=2)
    provider_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee_percent     = models.DecimalField(max_digits=5, decimal_places=2)
    paid_out        = models.BooleanField(default=False)


class Wallet(TimeStampedModel):
    user      = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance   = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_withdrawn = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class Payout(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        PROCESSING = 'processing', 'Processing'
        PAID       = 'paid',       'Paid'
        FAILED     = 'failed',     'Failed'

    provider       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payouts')
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transfer_code  = models.CharField(max_length=100, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
