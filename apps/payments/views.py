"""
Payment views — real Paystack integration.
Initialize → redirect to Paystack checkout → callback verify OR webhook.
Both verify_payment and webhook call on_payment_success (idempotent — safe to hit twice).
"""
import json, logging
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Payment, Wallet, Payout
from .paystack import Paystack, PaystackError
from .services import on_payment_success, on_payment_failed
from apps.bookings.models import Booking

logger = logging.getLogger('apps')


def _err(msg, status=400): return JsonResponse({'ok': False, 'error': msg}, status=status)
def _ok(data=None):         return JsonResponse({'ok': True, **(data or {})})


# ─────────────────────────────────────────────
# 1. INITIALIZE — customer hits "Book Now"
# ─────────────────────────────────────────────
@login_required
@require_POST
def initialize_payment(request):
    d = json.loads(request.body)
    booking_uid = d.get('booking_uid')

    try:
        booking = Booking.objects.select_related(
            'event', 'event__organizer'
        ).get(uid=booking_uid, customer=request.user, status='pending')
    except Booking.DoesNotExist:
        return _err('Booking not found or already paid.')

    # Get or create the Payment row
    payment, _ = Payment.objects.get_or_create(
        booking=booking, defaults={'amount': booking.total}
    )
    if payment.status == Payment.Status.SUCCESS:
        return _err('This booking is already paid.')

    # Free event — confirm immediately, no Paystack needed
    if booking.total == 0:
        on_payment_success(payment, {'channel': 'free', 'gateway_response': 'Free event'})
        return _ok({'free': True, 'redirect': '/my-tickets/'})

    # Call Paystack /transaction/initialize
    callback = f'{settings.FRONTEND_URL}/payments/callback/'
    ps = Paystack()
    try:
        data = ps.initialize(
            email=request.user.email,
            amount_ngn=booking.total,
            reference=payment.reference,
            callback_url=callback,
            metadata={
                'booking_reference': booking.reference,
                'event': booking.event.title,
                'customer': request.user.email,
                'custom_fields': [
                    {'display_name': 'Booking Ref', 'variable_name': 'booking_ref', 'value': booking.reference},
                    {'display_name': 'Event', 'variable_name': 'event', 'value': booking.event.title},
                ]
            }
        )
    except PaystackError as e:
        logger.error(f'Paystack initialize error: {e}')
        return _err(str(e), 502)

    payment.authorization_url = data.get('authorization_url', '')
    payment.access_code       = data.get('access_code', '')
    payment.paystack_ref      = data.get('reference', payment.reference)
    payment.save(update_fields=['authorization_url', 'access_code', 'paystack_ref'])

    logger.info(f'Payment initialized: {payment.reference} for ₦{booking.total}')
    return _ok({
        'authorization_url': payment.authorization_url,
        'reference': payment.reference,
        'amount': str(booking.total),
    })


# ─────────────────────────────────────────────
# 2. VERIFY — called after Paystack redirects
#    back to /payments/callback/?reference=...
# ─────────────────────────────────────────────
@login_required
def verify_payment(request, reference):
    """Idempotent — safe to call multiple times."""
    try:
        payment = Payment.objects.select_related(
            'booking__event', 'booking__customer'
        ).get(
            Q(reference=reference) | Q(paystack_ref=reference),
            booking__customer=request.user
        )
    except Payment.DoesNotExist:
        return _err('Payment not found.', 404)

    # Already processed
    if payment.status == Payment.Status.SUCCESS:
        return _ok({'status': 'success', 'already_processed': True})

    # Ask Paystack to confirm
    ps = Paystack()
    try:
        data = ps.verify(payment.paystack_ref or payment.reference)
    except PaystackError as e:
        logger.error(f'Paystack verify error: {e}')
        return _err(str(e), 502)

    ps_status   = data.get('status')              # 'success', 'failed', 'abandoned' …
    amount_paid = Decimal(str(data.get('amount', 0))) / 100   # Paystack sends kobo

    logger.info(f'Paystack verify {reference}: status={ps_status} amount_paid=₦{amount_paid} expected=₦{payment.amount}')

    if ps_status == 'success' and amount_paid >= payment.amount:
        on_payment_success(payment, data)
        return _ok({'status': 'success'})
    else:
        on_payment_failed(payment, data)
        return _ok({'status': payment.status, 'gateway': data.get('gateway_response', '')})


# ─────────────────────────────────────────────
# 3. WEBHOOK — Paystack server-to-server push
#    /api/payments/webhook/
#    Must be registered in Paystack dashboard!
# ─────────────────────────────────────────────
@csrf_exempt
@require_POST
def webhook(request):
    """
    Paystack signs every webhook with HMAC-SHA512 using your secret key.
    We verify the signature before processing anything.
    Register this URL in: dashboard.paystack.com → Settings → Webhooks
    """
    signature = request.headers.get('x-paystack-signature', '')
    raw_body  = request.body

    # Always respond 200 quickly so Paystack doesn't retry
    if not Paystack.verify_signature(raw_body, signature):
        logger.warning('Webhook rejected: invalid HMAC signature')
        return HttpResponse(status=401)

    try:
        event = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)

    event_type = event.get('event', '')
    data       = event.get('data', {})
    ref        = data.get('reference', '')

    logger.info(f'Webhook received: {event_type} ref={ref}')

    if not ref:
        return HttpResponse(status=200)

    # Find payment by our reference OR Paystack's reference
    payment = Payment.objects.select_related(
        'booking__event__organizer', 'booking__customer'
    ).filter(
        Q(reference=ref) | Q(paystack_ref=ref)
    ).first()

    if not payment:
        logger.warning(f'Webhook: unknown payment reference {ref}')
        return HttpResponse(status=200)   # 200 so Paystack doesn't retry

    # Store raw payload for audit
    payment.webhook_payload = event
    payment.save(update_fields=['webhook_payload'])

    if event_type == 'charge.success':
        amount_paid = Decimal(str(data.get('amount', 0))) / 100
        if amount_paid >= payment.amount:
            on_payment_success(payment, data)
        else:
            logger.warning(f'Webhook: underpayment ₦{amount_paid} < ₦{payment.amount}')

    elif event_type == 'charge.failed':
        on_payment_failed(payment, data)

    elif event_type == 'refund.processed':
        payment.status = Payment.Status.REFUNDED
        payment.save(update_fields=['status'])
        payment.booking.status = Booking.Status.REFUNDED
        payment.booking.save(update_fields=['status'])

    elif event_type == 'transfer.success':
        # A payout landed — mark the Payout record paid
        from .models import Payout
        transfer_code = data.get('transfer_code', '')
        if transfer_code:
            Payout.objects.filter(transfer_code=transfer_code).update(status='paid')

    elif event_type == 'transfer.failed':
        from .models import Payout
        transfer_code = data.get('transfer_code', '')
        reason = data.get('reason', 'Transfer failed')
        if transfer_code:
            Payout.objects.filter(transfer_code=transfer_code).update(
                status='failed', failure_reason=reason
            )

    return HttpResponse(status=200)


# ─────────────────────────────────────────────
# 4. WALLET & PAYOUTS
# ─────────────────────────────────────────────
@login_required
def wallet_view(request):
    if not request.user.is_provider:
        return _err('Provider account required.', 403)
    w, _ = Wallet.objects.get_or_create(user=request.user)
    return _ok({
        'balance':           str(w.balance),
        'total_earned':      str(w.total_earned),
        'total_withdrawn':   str(w.total_withdrawn),
    })


@login_required
@require_POST
def request_payout(request):
    if not request.user.is_provider:
        return _err('Provider account required.', 403)

    d      = json.loads(request.body)
    amount = Decimal(str(d.get('amount', 0)))

    if amount < Decimal('1000'):
        return _err('Minimum payout is ₦1,000.')

    w, _ = Wallet.objects.get_or_create(user=request.user)
    if amount > w.balance:
        return _err(f'Insufficient balance. Available: ₦{w.balance:,.0f}')

    rc = request.user.paystack_recipient_code
    if not rc:
        return _err('No bank account linked. Add your bank details in your profile first.')

    payout = Payout.objects.create(
        provider=request.user, amount=amount, status=Payout.Status.PROCESSING
    )
    ps = Paystack()
    try:
        result = ps.transfer(
            amount_ngn=amount,
            recipient_code=rc,
            reason='EventBook provider payout',
            reference=f'PAYOUT-{payout.pk}'
        )
        payout.transfer_code = result.get('transfer_code', '')
        payout.status = Payout.Status.PROCESSING
        payout.save()

        # Deduct from wallet immediately; webhook confirms final status
        w.balance        -= amount
        w.total_withdrawn += amount
        w.save()

        logger.info(f'Payout initiated: ₦{amount} to {request.user.email} code={payout.transfer_code}')
        return _ok({'message': f'Payout of ₦{amount:,.0f} initiated. It will arrive within 24 hours.'})

    except PaystackError as e:
        payout.status = Payout.Status.FAILED
        payout.failure_reason = str(e)
        payout.save()
        return _err(str(e), 502)


@login_required
def my_payouts(request):
    payouts = Payout.objects.filter(
        provider=request.user
    ).order_by('-created_at')[:50]
    return _ok({'results': [{
        'id':           p.pk,
        'amount':       str(p.amount),
        'status':       p.status,
        'transfer_code': p.transfer_code,
        'created_at':   p.created_at.isoformat(),
    } for p in payouts]})
