import random, string
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel, UUIDModel
from apps.events.models import Event, TicketType

def gen_ref():
    return 'BK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

class Booking(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending Payment'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED  = 'refunded',  'Refunded'

    reference   = models.CharField(max_length=20, unique=True, default=gen_ref, editable=False)
    customer    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, null=True, blank=True, related_name='bookings')
    quantity    = models.PositiveSmallIntegerField(default=1)
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    total       = models.DecimalField(max_digits=12, decimal_places=2)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attendee_name  = models.CharField(max_length=150, blank=True)
    attendee_email = models.EmailField(blank=True)
    attendee_phone = models.CharField(max_length=20, blank=True)
    cancelled_at   = models.DateTimeField(null=True, blank=True)
    cancel_reason  = models.CharField(max_length=255, blank=True)

    class Meta: ordering = ['-created_at']

    @property
    def is_cancellable(self):
        from django.utils import timezone
        return self.status == 'confirmed' and self.event.start_datetime > timezone.now()

    def __str__(self): return f'{self.reference} — {self.event.title}'
