from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def list_notifications(request):
    notifs = Notification.objects.filter(user=request.user)[:50]
    return JsonResponse({'results': [{
        'id': n.id, 'title': n.title, 'message': n.message,
        'kind': n.kind, 'is_read': n.is_read, 'link': n.link,
        'created_at': n.created_at.isoformat(),
    } for n in notifs]})


@login_required
def unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
@require_POST
def mark_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})
