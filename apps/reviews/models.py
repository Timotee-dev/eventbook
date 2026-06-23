from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.events.models import Event

class Review(TimeStampedModel):
    customer    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews')
    rating      = models.PositiveSmallIntegerField()
    comment     = models.TextField(max_length=1000, blank=True)
    is_approved = models.BooleanField(default=True)

    class Meta:
        unique_together = ('customer', 'event')
        ordering = ['-created_at']
