from django.conf import settings
from django.db import models
from django.utils.text import slugify
from apps.core.models import TimeStampedModel, UUIDModel

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=10, default='✦')

    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self): return self.name
    class Meta: verbose_name_plural = 'Categories'; ordering = ['name']


class Event(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        PENDING   = 'pending',   'Pending Review'
        PUBLISHED = 'published', 'Published'
        REJECTED  = 'rejected',  'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    organizer      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='events')
    category       = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='events')
    title          = models.CharField(max_length=200)
    slug           = models.SlugField(max_length=220, unique=True, blank=True)
    short_desc     = models.CharField(max_length=300, blank=True)
    description    = models.TextField()
    banner         = models.ImageField(upload_to='events/banners/', blank=True, null=True)
    venue_name     = models.CharField(max_length=200)
    address        = models.CharField(max_length=255, blank=True)
    city           = models.CharField(max_length=100)
    state          = models.CharField(max_length=100, blank=True)
    is_online      = models.BooleanField(default=False)
    online_link    = models.URLField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime   = models.DateTimeField()
    capacity       = models.PositiveIntegerField(default=100)
    base_price     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_featured    = models.BooleanField(default=False)
    view_count     = models.PositiveIntegerField(default=0)
    rejection_note = models.CharField(max_length=255, blank=True)
    is_deleted     = models.BooleanField(default=False)

    class Meta: ordering = ['-start_datetime']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200]
            slug, n = base, 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'; n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_free(self): return self.base_price == 0

    @property
    def tickets_sold(self):
        return sum(t.sold for t in self.ticket_types.all())

    @property
    def is_sold_out(self): return self.tickets_sold >= self.capacity

    @property
    def avg_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if not reviews.exists(): return 0
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def __str__(self): return self.title


class TicketType(TimeStampedModel):
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    name        = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    price       = models.DecimalField(max_digits=12, decimal_places=2)
    quantity    = models.PositiveIntegerField()
    sold        = models.PositiveIntegerField(default=0)
    max_per_customer = models.PositiveSmallIntegerField(default=10)
    is_active   = models.BooleanField(default=True)

    @property
    def remaining(self): return max(self.quantity - self.sold, 0)
    @property
    def is_sold_out(self): return self.remaining <= 0
    def __str__(self): return f'{self.event.title} — {self.name}'
