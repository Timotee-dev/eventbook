"""
Transactional emails using Django's built-in mail system.
No third-party packages needed.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger('apps')

def send(subject, template, context, to):
    context = {**context, 'SITE_NAME': settings.SITE_NAME, 'FRONTEND_URL': settings.FRONTEND_URL}
    try:
        html = render_to_string(f'emails/{template}.html', context)
        txt  = render_to_string(f'emails/{template}.txt',  context)
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(subject, txt, settings.DEFAULT_FROM_EMAIL, [to])
        msg.attach_alternative(html, 'text/html')
        msg.send()
    except Exception as e:
        logger.error(f'Email failed to {to}: {e}')

def send_verify_email(user, token):
    url = f'{settings.FRONTEND_URL}/verify-email/{token}/'
    send('Verify your email', 'verify_email', {'user': user, 'url': url}, user.email)

def send_password_reset(user, token):
    url = f'{settings.FRONTEND_URL}/reset-password/{token}/'
    send('Reset your password', 'password_reset', {'user': user, 'url': url}, user.email)

def send_booking_confirmation(booking):
    send(f'Booking Confirmed: {booking.event.title}', 'booking_confirm',
         {'booking': booking, 'event': booking.event}, booking.customer.email)

def send_payment_receipt(payment):
    send(f'Payment Receipt — {payment.reference}', 'payment_receipt',
         {'payment': payment, 'booking': payment.booking}, payment.booking.customer.email)
