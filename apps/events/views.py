import json
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F, Avg
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Event, Category, TicketType
from apps.reviews.models import Review


def _json(data, status=200): return JsonResponse(data, status=status, safe=isinstance(data, dict))
def _err(msg, status=400):   return JsonResponse({'ok': False, 'error': msg}, status=status)
def _ok(data=None):           return JsonResponse({'ok': True, **(data or {})})

def _serialize_event(e, short=True):
    d = {
        'uid': str(e.uid), 'slug': e.slug, 'title': e.title,
        'short_desc': e.short_desc, 'category': e.category.name if e.category else '',
        'category_icon': e.category.icon if e.category else '✦',
        'venue_name': e.venue_name, 'city': e.city, 'state': e.state,
        'is_online': e.is_online, 'start_datetime': e.start_datetime.isoformat(),
        'end_datetime': e.end_datetime.isoformat(),
        'base_price': str(e.base_price), 'is_free': e.is_free,
        'status': e.status, 'is_featured': e.is_featured,
        'view_count': e.view_count, 'is_sold_out': e.is_sold_out,
        'avg_rating': e.avg_rating, 'tickets_sold': e.tickets_sold,
        'banner': e.banner.url if e.banner else None,
        'organizer': e.organizer.get_full_name() or e.organizer.username,
        'organizer_id': e.organizer_id,
    }
    if not short:
        d['description'] = e.description
        d['address'] = e.address
        d['online_link'] = e.online_link
        d['rejection_note'] = e.rejection_note
        d['ticket_types'] = [{
            'id': t.id, 'name': t.name, 'description': t.description,
            'price': str(t.price), 'quantity': t.quantity,
            'remaining': t.remaining, 'is_sold_out': t.is_sold_out,
            'max_per_customer': t.max_per_customer,
        } for t in e.ticket_types.filter(is_active=True)]
        reviews = e.reviews.filter(is_approved=True)[:10]
        d['reviews'] = [{
            'customer': r.customer.get_full_name() or r.customer.username,
            'rating': r.rating, 'comment': r.comment,
            'created_at': r.created_at.isoformat(),
        } for r in reviews]
        d['review_count'] = e.reviews.filter(is_approved=True).count()
    return d


def events_list(request):
    qs = Event.objects.filter(status='published', is_deleted=False).select_related('category','organizer').prefetch_related('ticket_types','reviews')
    search = request.GET.get('q','').strip()
    cat    = request.GET.get('category','')
    city   = request.GET.get('city','')
    min_p  = request.GET.get('min_price','')
    max_p  = request.GET.get('max_price','')
    is_free= request.GET.get('is_free','')
    is_online = request.GET.get('is_online','')
    sort   = request.GET.get('sort','start_datetime')
    page   = int(request.GET.get('page', 1))

    if search: qs = qs.filter(Q(title__icontains=search)|Q(description__icontains=search)|Q(city__icontains=search))
    if cat:    qs = qs.filter(category__slug=cat)
    if city:   qs = qs.filter(city__icontains=city)
    if min_p:  qs = qs.filter(base_price__gte=min_p)
    if max_p:  qs = qs.filter(base_price__lte=max_p)
    if is_free == 'true': qs = qs.filter(base_price=0)
    if is_online == 'true': qs = qs.filter(is_online=True)
    if sort in ('start_datetime','-start_datetime','base_price','-base_price','-view_count'):
        qs = qs.order_by(sort)

    paginator = Paginator(qs, 12)
    page_obj  = paginator.get_page(page)
    return _json({
        'count': paginator.count,
        'pages': paginator.num_pages,
        'page': page,
        'results': [_serialize_event(e) for e in page_obj],
    })


def event_detail_api(request, slug):
    try:
        e = Event.objects.select_related('category','organizer').prefetch_related('ticket_types','reviews').get(slug=slug, is_deleted=False)
    except Event.DoesNotExist:
        return _err('Event not found.', 404)
    if e.status != 'published' and (not request.user.is_authenticated or (request.user != e.organizer and not request.user.is_admin_role)):
        return _err('Event not found.', 404)
    Event.objects.filter(pk=e.pk).update(view_count=F('view_count') + 1)
    return _json(_serialize_event(e, short=False))


def event_detail_page(request, slug):
    return render(request, 'core/event_detail.html', {'slug': slug})


def categories_list(request):
    cats = Category.objects.all()
    return _json({'results': [{'name': c.name, 'slug': c.slug, 'icon': c.icon} for c in cats]})


@login_required
def create_event(request):
    if not request.user.is_provider:
        return _err('Provider account required.', 403)
    if request.method != 'POST':
        return _err('POST required.')
    d = json.loads(request.body)
    required = ['title','description','venue_name','city','start_datetime','end_datetime','capacity']
    for f in required:
        if not d.get(f):
            return _err(f'"{f}" is required.')
    from datetime import datetime
    try:
        start = datetime.fromisoformat(d['start_datetime'].replace('Z','+00:00'))
        end   = datetime.fromisoformat(d['end_datetime'].replace('Z','+00:00'))
    except Exception:
        return _err('Invalid date format.')
    if start >= end:
        return _err('Start must be before end.')

    cat = None
    if d.get('category_id'):
        try: cat = Category.objects.get(pk=d['category_id'])
        except Category.DoesNotExist: pass

    e = Event.objects.create(
        organizer=request.user, category=cat,
        title=d['title'], short_desc=d.get('short_desc',''),
        description=d['description'], venue_name=d['venue_name'],
        address=d.get('address',''), city=d['city'], state=d.get('state',''),
        is_online=d.get('is_online', False), online_link=d.get('online_link',''),
        start_datetime=start, end_datetime=end,
        capacity=int(d['capacity']), base_price=d.get('base_price', 0),
        status='pending',
    )
    return _json({'ok': True, 'slug': e.slug, 'uid': str(e.uid)}, 201)


@login_required
def add_ticket_type(request, slug):
    try:
        e = Event.objects.get(slug=slug, organizer=request.user)
    except Event.DoesNotExist:
        return _err('Event not found.', 404)
    d = json.loads(request.body)
    TicketType.objects.create(
        event=e, name=d['name'], description=d.get('description',''),
        price=d['price'], quantity=int(d['quantity']),
        max_per_customer=int(d.get('max_per_customer', 10)),
    )
    return _ok()


@login_required
def my_events(request):
    if not request.user.is_provider:
        return _err('Provider only.', 403)
    qs = Event.objects.filter(organizer=request.user, is_deleted=False).select_related('category')
    return _json({'results': [_serialize_event(e) for e in qs]})


@login_required
def submit_event(request, slug):
    try:
        e = Event.objects.get(slug=slug, organizer=request.user)
    except Event.DoesNotExist:
        return _err('Not found.', 404)
    if e.status not in ('draft','rejected'):
        return _err('Cannot resubmit.')
    e.status = 'pending'; e.rejection_note = ''; e.save()
    return _ok()


@login_required
def post_review(request, slug):
    d = json.loads(request.body)
    try:
        e = Event.objects.get(slug=slug, status='published')
    except Event.DoesNotExist:
        return _err('Event not found.', 404)
    from apps.bookings.models import Booking
    if not Booking.objects.filter(customer=request.user, event=e, status='confirmed').exists():
        return _err('You can only review events you have attended.')
    if e.start_datetime > timezone.now():
        return _err('You can only review after the event has started.')
    rating = int(d.get('rating', 0))
    if not 1 <= rating <= 5:
        return _err('Rating must be 1–5.')
    Review.objects.update_or_create(
        customer=request.user, event=e,
        defaults={'rating': rating, 'comment': d.get('comment','')},
    )
    return _ok()
