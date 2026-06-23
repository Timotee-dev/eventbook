from django.contrib import admin
from .models import Event, Category, TicketType

class TicketTypeInline(admin.TabularInline):
    model = TicketType; extra = 0

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title','organizer','status','city','start_datetime','is_featured')
    list_filter  = ('status','is_featured','is_online','category')
    search_fields= ('title','organizer__email','city')
    inlines      = [TicketTypeInline]
    actions      = ['publish','reject']
    readonly_fields = ('view_count','uid','slug')

    @admin.action(description='Publish selected events')
    def publish(self, request, qs):
        qs.update(status='published')

    @admin.action(description='Reject selected events')
    def reject(self, request, qs):
        qs.update(status='rejected')

admin.site.register(Category)
