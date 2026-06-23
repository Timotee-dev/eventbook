from django.contrib import admin
from .models import Booking
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference','customer','event','quantity','total','status','created_at')
    list_filter  = ('status',); search_fields = ('reference','customer__email','event__title')
