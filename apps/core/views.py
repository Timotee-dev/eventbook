from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect


def home(request): return render(request, 'core/home.html')
def browse(request): return render(request, 'core/browse.html')
def event_detail(request, slug): return render(request, 'core/event_detail.html', {'slug': slug})
def login_page(request): return render(request, 'core/login.html')
def register_page(request): return render(request, 'core/register.html')
def verify_email_page(request, token): return render(request, 'core/verify_email.html', {'token': str(token)})
def reset_password_page(request, token): return render(request, 'core/reset_password.html', {'token': str(token)})
def verify_ticket_page(request, number): return render(request, 'core/verify_ticket.html', {'number': number})
def payment_callback(request): return render(request, 'core/payment_callback.html')

@login_required
def dashboard(request):
    u = request.user
    if u.is_provider: return render(request, 'core/dashboard_provider.html')
    if u.is_admin_role: return render(request, 'core/dashboard_admin.html')
    return render(request, 'core/dashboard_customer.html')

@login_required
def my_tickets_page(request): return render(request, 'core/my_tickets.html')

@login_required
def analytics_provider(request):
    if not request.user.is_provider:
        return JsonResponse({'error': 'Provider only'}, status=403)
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Sum, Count
    from apps.payments.models import RevenueSplit
    from apps.bookings.models import Booking
    from apps.events.models import Event

    days = int(request.GET.get('days', 30))
    since = timezone.now() - timedelta(days=days)
    user = request.user

    splits = RevenueSplit.objects.filter(provider=user, created_at__gte=since)
    total_revenue = splits.aggregate(t=Sum('provider_amount'))['t'] or 0
    total_tickets = Booking.objects.filter(
        event__organizer=user, status='confirmed', created_at__gte=since
    ).aggregate(t=Sum('quantity'))['t'] or 0
    active_events = Event.objects.filter(organizer=user, status='published', is_deleted=False).count()

    from apps.payments.models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=user)

    top_events = Event.objects.filter(organizer=user, is_deleted=False).annotate(
        bookings_count=Count('bookings', filter=__import__('django.db.models',fromlist=['Q']).Q(bookings__status='confirmed')),
        revenue=Sum('bookings__total', filter=__import__('django.db.models',fromlist=['Q']).Q(bookings__status='confirmed')),
    ).values('title','slug','capacity','bookings_count','revenue').order_by('-revenue')[:8]

    return JsonResponse({
        'total_revenue': str(total_revenue),
        'total_tickets': total_tickets,
        'active_events': active_events,
        'wallet_balance': str(wallet.balance),
        'top_events': list(top_events),
    })


@login_required
def analytics_admin(request):
    if not request.user.is_admin_role:
        return JsonResponse({'error': 'Admin only'}, status=403)
    from apps.accounts.models import User
    from apps.events.models import Event
    from apps.payments.models import Payment, RevenueSplit
    from django.db.models import Sum

    platform_rev = RevenueSplit.objects.aggregate(t=Sum('platform_amount'))['t'] or 0
    gross_vol    = Payment.objects.filter(status='success').aggregate(t=Sum('amount'))['t'] or 0

    return JsonResponse({
        'total_users': User.objects.count(),
        'total_customers': User.objects.filter(role='customer').count(),
        'total_providers': User.objects.filter(role='provider').count(),
        'pending_providers': User.objects.filter(role='provider', is_provider_approved=False).count(),
        'total_events': Event.objects.count(),
        'pending_events': Event.objects.filter(status='pending').count(),
        'platform_revenue': str(platform_rev),
        'gross_volume': str(gross_vol),
    })
