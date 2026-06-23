from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static

# Page views
from apps.core.views import (
    home, browse, event_detail, login_page, register_page,
    verify_email_page, reset_password_page, verify_ticket_page,
    payment_callback, dashboard, my_tickets_page,
    analytics_provider, analytics_admin,
)
from apps.accounts.views import (
    register_view, login_view, logout_view, verify_email_view,
    resend_verify, password_reset_request, password_reset_confirm,
    me_view, change_password,
)
from apps.events.views import (
    events_list, event_detail_api, event_detail_page, categories_list,
    create_event, add_ticket_type, my_events, submit_event, post_review,
)
from apps.bookings.views import create_booking, my_bookings, cancel_booking
from apps.payments.views import (
    initialize_payment, verify_payment, webhook,
    wallet_view, request_payout, my_payouts,
)
from apps.tickets.views import my_tickets, verify_ticket, scan_ticket
from apps.notifications.views import (
    list_notifications, unread_count, mark_read, mark_all_read,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Pages ──
    path('', home, name='home'),
    path('events/', browse, name='browse'),
    path('events/<slug:slug>/', event_detail, name='event_detail'),
    path('login/', login_page, name='login'),
    path('register/', register_page, name='register'),
    path('dashboard/', dashboard, name='dashboard'),
    path('my-tickets/', my_tickets_page, name='my_tickets_page'),
    path('verify-email/<uuid:token>/', verify_email_page, name='verify_email_page'),
    path('reset-password/<uuid:token>/', reset_password_page, name='reset_password_page'),
    path('verify-ticket/<str:number>/', verify_ticket_page, name='verify_ticket_page'),
    path('payments/callback/', payment_callback, name='payment_callback'),

    # ── API: Auth ──
    path('api/auth/register/',          register_view,           name='api_register'),
    path('api/auth/login/',             login_view,              name='api_login'),
    path('api/auth/logout/',            logout_view,             name='api_logout'),
    path('api/auth/me/',                me_view,                 name='api_me'),
    path('api/auth/change-password/',   change_password,         name='api_change_pw'),
    path('api/auth/verify-email/<uuid:token>/', verify_email_view, name='api_verify_email'),
    path('api/auth/resend-verify/',     resend_verify,           name='api_resend_verify'),
    path('api/auth/password-reset/',    password_reset_request,  name='api_pw_reset'),
    path('api/auth/password-reset/<uuid:token>/', password_reset_confirm, name='api_pw_reset_confirm'),

    # ── API: Events ──
    path('api/events/',                     events_list,         name='api_events'),
    path('api/events/categories/',          categories_list,     name='api_categories'),
    path('api/events/mine/',                my_events,           name='api_my_events'),
    path('api/events/create/',              create_event,        name='api_create_event'),
    path('api/events/<slug:slug>/',         event_detail_api,    name='api_event_detail'),
    path('api/events/<slug:slug>/ticket-types/', add_ticket_type, name='api_add_tt'),
    path('api/events/<slug:slug>/submit/',  submit_event,        name='api_submit_event'),
    path('api/events/<slug:slug>/review/',  post_review,         name='api_review'),

    # ── API: Bookings ──
    path('api/bookings/',              create_booking, name='api_create_booking'),
    path('api/bookings/mine/',         my_bookings,    name='api_my_bookings'),
    path('api/bookings/<uuid:uid>/cancel/', cancel_booking, name='api_cancel_booking'),

    # ── API: Payments ──
    path('api/payments/initialize/',              initialize_payment, name='api_pay_init'),
    path('api/payments/verify/<str:reference>/',  verify_payment,     name='api_pay_verify'),
    path('api/payments/webhook/',                 webhook,            name='api_webhook'),
    path('api/payments/wallet/',                  wallet_view,        name='api_wallet'),
    path('api/payments/payout/',                  request_payout,     name='api_payout'),
    path('api/payments/payouts/',                 my_payouts,         name='api_my_payouts'),

    # ── API: Tickets ──
    path('api/tickets/mine/',             my_tickets,    name='api_my_tickets'),
    path('api/tickets/verify/<str:number>/', verify_ticket, name='api_verify_ticket'),
    path('api/tickets/scan/',             scan_ticket,   name='api_scan_ticket'),

    # ── API: Notifications ──
    path('api/notifications/',            list_notifications, name='api_notifs'),
    path('api/notifications/unread/',     unread_count,       name='api_unread'),
    path('api/notifications/mark-all/',   mark_all_read,      name='api_mark_all'),
    path('api/notifications/<int:pk>/read/', mark_read,       name='api_mark_read'),

    # ── API: Analytics ──
    path('api/analytics/provider/', analytics_provider, name='api_analytics_provider'),
    path('api/analytics/admin/',    analytics_admin,    name='api_analytics_admin'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
