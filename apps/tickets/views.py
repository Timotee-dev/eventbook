from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from .models import Ticket
from apps.payments.models import Payment


def _err(msg, s=400): return JsonResponse({'ok': False, 'error': msg}, status=s)
def _ok(d=None): return JsonResponse({'ok': True, **(d or {})})

def _serialize(t):
    return {
        'number': t.number, 'status': t.status,
        'event_title': t.booking.event.title,
        'event_start': t.booking.event.start_datetime.isoformat(),
        'venue': t.booking.event.venue_name,
        'city': t.booking.event.city,
        'booking_ref': t.booking.reference,
        'quantity': t.booking.quantity,
        'attendee_name': t.booking.attendee_name,
        'ticket_type': t.booking.ticket_type.name if t.booking.ticket_type else 'General',
        'qr_image': t.qr_image.url if t.qr_image else None,
        'pdf_file': t.pdf_file.url if t.pdf_file else None,
        'checked_in_at': t.checked_in_at.isoformat() if t.checked_in_at else None,
    }


@login_required
def my_tickets(request):
    tickets = Ticket.objects.filter(
        booking__customer=request.user
    ).select_related('booking__event','booking__ticket_type').order_by('-created_at')
    return JsonResponse({'results': [_serialize(t) for t in tickets]})


def verify_ticket(request, number):
    """Public endpoint for QR scan verification."""
    try:
        t = Ticket.objects.select_related('booking__event').get(number=number)
    except Ticket.DoesNotExist:
        return _err('Ticket not found.', 404)
    return JsonResponse({
        'valid': t.is_valid, 'status': t.status,
        'event_title': t.booking.event.title,
        'attendee_name': t.booking.attendee_name,
        'quantity': t.booking.quantity,
        'checked_in_at': t.checked_in_at.isoformat() if t.checked_in_at else None,
    })


@login_required
@require_POST
def scan_ticket(request):
    """Provider check-in endpoint."""
    if not request.user.is_provider:
        return _err('Provider only.', 403)
    d = json.loads(request.body)
    number = d.get('ticket_number','')
    try:
        t = Ticket.objects.select_related('booking__event').get(number=number)
    except Ticket.DoesNotExist:
        return _err('Ticket not found.')
    if t.booking.event.organizer != request.user and not request.user.is_admin_role:
        return _err('You do not manage this event.', 403)
    if t.status == 'used':
        return _err(f'Already checked in at {t.checked_in_at}.', 400)
    if t.status == 'cancelled':
        return _err('Ticket is cancelled.', 400)

    from django.utils import timezone
    t.status = 'used'
    t.checked_in_at = timezone.now()
    t.checked_in_by = d.get('scanner','') or request.user.email
    t.save()
    return _ok({'message': 'Check-in successful!', 'attendee': t.booking.attendee_name})
