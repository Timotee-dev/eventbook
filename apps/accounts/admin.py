from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, EmailToken

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email','username','role','is_email_verified','is_provider_approved','is_active','date_joined')
    list_filter  = ('role','is_email_verified','is_provider_approved')
    search_fields= ('email','username','first_name','last_name')
    ordering     = ('-date_joined',)
    fieldsets    = UserAdmin.fieldsets + (
        ('EventBook', {'fields': ('role','phone','is_email_verified','is_provider_approved','bio','company_name','city','state','bank_name','bank_account_number','bank_account_name','paystack_recipient_code')}),
    )
    actions = ['approve_providers']

    @admin.action(description='Approve selected providers')
    def approve_providers(self, request, queryset):
        n = queryset.filter(role='provider').update(is_provider_approved=True)
        self.message_user(request, f'{n} provider(s) approved.')

admin.site.register(EmailToken)
