"""
Payment processing: revenue split (95/5), wallet credit, ticket generation,
notification sending. Idempotent — safe to call twice for same payment.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Payment, RevenueSplit, Wallet
from apps.bookings.models import Booking
from apps.notifications.models import Notification

logger = logging.getLogger('apps')


@transaction.atomic
def on_payment_success(payment: Payment, data: dict):
    if payment.status == Payment.Status.SUCCESS:
        return  # idempotent

    payment.status          = Payment.Status.SUCCESS
    payment.channel         = data.get('channel', '')
    payment.gateway_response= data.get('gateway_response', '')
    payment.paid_at         = timezone.now()
    payment.paystack_ref    = data.get('reference', payment.paystack_ref)
    payment.save()

    booking = payment.booking
    booking.status = Booking.Status.CONFIRMED
    booking.save()

    # Increment ticket_type sold count
    if booking.ticket_type_id:
        from apps.events.models import TicketType
        from django.db.models import F
        TicketType.objects.filter(pk=booking.ticket_type_id).update(sold=F('sold') + booking.quantity)

    # Revenue split
    fee_pct = Decimal(str(settings.PLATFORM_FEE_PERCENT))
    gross   = payment.amount
    plat    = (gross * fee_pct / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
    prov    = gross - plat

    RevenueSplit.objects.update_or_create(
        payment=payment,
        defaults={
            'provider': booking.event.organizer,
            'gross': gross, 'provider_amount': prov,
            'platform_amount': plat, 'fee_percent': fee_pct,
        }
    )

    wallet, _ = Wallet.objects.get_or_create(user=booking.event.organizer)
    wallet.balance      += prov
    wallet.total_earned += prov
    wallet.save()

    # Generate ticket
    from apps.tickets.services import make_ticket
    make_ticket(booking)

    # Notifications
    Notification.objects.create(
        user=booking.customer, kind='booking',
        title='Booking Confirmed ✓',
        message=f'Your booking for "{booking.event.title}" is confirmed.',
        link=f'/my-tickets/',
    )
    Notification.objects.create(
        user=booking.event.organizer, kind='payment',
        title='New Ticket Sale 💰',
        message=f'{booking.quantity} ticket(s) sold for "{booking.event.title}". You earned ₦{prov:,.0f}.',
    )

    # Emails (fire and forget)
    try:
        from apps.notifications.email import send_booking_confirmation, send_payment_receipt
        send_booking_confirmation(booking)
        send_payment_receipt(payment)
    except Exception as e:
        logger.error(f'Email error: {e}')

    logger.info(f'Payment {payment.reference} processed. Provider: ₦{prov}, Platform: ₦{plat}')


def on_payment_failed(payment: Payment, data: dict):
    if payment.status == Payment.Status.SUCCESS:
        return
    payment.status = Payment.Status.FAILED
    payment.gateway_response = data.get('gateway_response', 'Failed')
    payment.save()
    booking = payment.booking
    booking.status = Booking.Status.CANCELLED
    booking.save()
    Notification.objects.create(
        user=booking.customer, kind='payment',
        title='Payment Failed',
        message=f'Your payment for "{booking.event.title}" was not completed.',
    )
