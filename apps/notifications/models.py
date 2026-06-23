from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Notification(TimeStampedModel):
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title   = models.CharField(max_length=150)
    message = models.CharField(max_length=500)
    kind    = models.CharField(max_length=20, default='info')
    is_read = models.BooleanField(default=False)
    link    = models.CharField(max_length=255, blank=True)

    class Meta: ordering = ['-created_at']
