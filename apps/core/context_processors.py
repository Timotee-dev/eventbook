from django.conf import settings
def site_settings(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
        'DEBUG': settings.DEBUG,
    }
