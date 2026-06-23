import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from .models import Booking
from apps.events.models import Event, TicketType


def _err(msg, status=400): return JsonResponse({'ok': False, 'error': msg}, status=status)
def _ok(data=None):         return JsonResponse({'ok': True, **(data or {})})

def _serialize(b):
    return {
        'uid': str(b.uid), 'reference': b.reference,
        'event_title': b.event.title, 'event_slug': b.event.slug,
        'event_start': b.event.start_datetime.isoformat(),
        'event_city': b.event.city,
        'ticket_type': b.ticket_type.name if b.ticket_type else 'General',
        'quantity': b.quantity, 'unit_price': str(b.unit_price),
        'total': str(b.total), 'status': b.status,
        'attendee_name': b.attendee_name, 'attendee_email': b.attendee_email,
        'is_cancellable': b.is_cancellable,
        'created_at': b.created_at.isoformat(),
        'ticket_number': b.ticket.number if hasattr(b, 'ticket') else None,
    }


@login_required
def create_booking(request):
    if request.method != 'POST':
        return _err('POST required.')
    d = json.loads(request.body)
    event_uid = d.get('event_uid')
    try:
        event = Event.objects.get(uid=event_uid, status='published', is_deleted=False)
    except Event.DoesNotExist:
        return _err('Event not found.')

    if event.start_datetime <= timezone.now():
        return _err('This event has already started.')

    qty = int(d.get('quantity', 1))
    if qty < 1: return _err('Quantity must be at least 1.')

    ticket_type = None
    tt_id = d.get('ticket_type_id')
    if tt_id:
        try:
            ticket_type = TicketType.objects.get(pk=tt_id, event=event, is_active=True)
        except TicketType.DoesNotExist:
            return _err('Ticket type not found.')
        if ticket_type.is_sold_out:
            return _err(f'"{ticket_type.name}" is sold out.')
        if qty > ticket_type.remaining:
            return _err(f'Only {ticket_type.remaining} ticket(s) left.')
        if qty > ticket_type.max_per_customer:
            return _err(f'Max {ticket_type.max_per_customer} per customer.')
        unit_price = ticket_type.price
    else:
        if event.is_sold_out:
            return _err('This event is sold out.')
        unit_price = event.base_price

    booking = Booking.objects.create(
        customer=request.user, event=event, ticket_type=ticket_type,
        quantity=qty, unit_price=unit_price, total=unit_price * qty,
        attendee_name=d.get('attendee_name','') or request.user.get_full_name() or request.user.username,
        attendee_email=d.get('attendee_email','') or request.user.email,
        attendee_phone=d.get('attendee_phone',''),
        status='pending',
    )
    return JsonResponse({'ok': True, 'booking': _serialize(booking)}, status=201)


@login_required
def my_bookings(request):
    qs = Booking.objects.filter(customer=request.user).select_related('event','ticket_type').prefetch_related('ticket').order_by('-created_at')
    status = request.GET.get('status','')
    if status: qs = qs.filter(status=status)
    return JsonResponse({'results': [_serialize(b) for b in qs]})


@login_required
def cancel_booking(request, uid):
    if request.method != 'POST': return _err('POST required.')
    try:
        b = Booking.objects.get(uid=uid, customer=request.user)
    except Booking.DoesNotExist:
        return _err('Booking not found.', 404)
    if not b.is_cancellable:
        return _err('This booking cannot be cancelled.')
    d = json.loads(request.body)
    b.status = 'cancelled'
    b.cancelled_at = timezone.now()
    b.cancel_reason = d.get('reason','')
    b.save()
    if b.ticket_type_id:
        from django.db.models import F
        TicketType.objects.filter(pk=b.ticket_type_id).update(sold=F('sold') - b.quantity)
    return _ok({'message': 'Booking cancelled.'})
