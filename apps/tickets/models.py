import uuid
from django.db import models
from apps.core.models import TimeStampedModel
from apps.bookings.models import Booking

def gen_ticket():
    return 'TKT-' + uuid.uuid4().hex[:12].upper()

class Ticket(TimeStampedModel):
    class Status(models.TextChoices):
        VALID     = 'valid',     'Valid'
        USED      = 'used',      'Used'
        CANCELLED = 'cancelled', 'Cancelled'

    booking       = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='ticket')
    number        = models.CharField(max_length=30, unique=True, default=gen_ticket, editable=False)
    qr_image      = models.ImageField(upload_to='tickets/qr/', blank=True, null=True)
    pdf_file      = models.FileField(upload_to='tickets/pdf/', blank=True, null=True)
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.VALID)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.CharField(max_length=150, blank=True)

    @property
    def is_valid(self): return self.status == 'valid'
    def __str__(self): return self.number
