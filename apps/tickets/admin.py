from django.contrib import admin
from .models import Ticket
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('number','booking','status','checked_in_at')
    list_filter  = ('status',)
