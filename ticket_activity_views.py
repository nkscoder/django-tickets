import json

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tickets.conf import get_setting

from .models import TicketActionTrace, TicketNotification


def _login_required(view):
    return login_required(login_url=get_setting("LOGIN_URL"))(view)


@_login_required
def ticket_activity_dashboard(request):
    """Optional integration with an ``activity`` app; works without it."""
    unread = TicketNotification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    context = {
        "unread_notifications": unread,
        "total_logs": 0,
        "visit_labels_json": json.dumps([]),
        "visit_values_json": json.dumps([]),
        "action_labels_json": json.dumps([]),
        "action_values_json": json.dumps([]),
        "recent_logs": [],
        "search_logs": [],
        "action_traces": TicketActionTrace.objects.select_related("ticket", "performed_by")
        .order_by("-performed_at")[:20],
    }

    if get_setting("ENABLE_ACTIVITY_DASHBOARD") and apps.is_installed("activity"):
        from activity.models import UserActivityLog
        from activity.utils import page_title_from_path

        ticket_logs = UserActivityLog.objects.filter(
            Q(path__startswith="/tickets/") | Q(object_type="Ticket")
        )
        context["total_logs"] = ticket_logs.count()
        visit_rows = (
            ticket_logs.filter(event_type="PAGE_VIEW")
            .values("path")
            .annotate(visits=Count("id"))
            .order_by("-visits")[:10]
        )
        visit_bucket = {}
        for row in visit_rows:
            title = page_title_from_path(row["path"]) or row["path"]
            visit_bucket[title] = visit_bucket.get(title, 0) + int(row["visits"] or 0)
        visit_items = sorted(visit_bucket.items(), key=lambda x: x[1], reverse=True)[:10]
        context["visit_labels_json"] = json.dumps([k for k, _ in visit_items])
        context["visit_values_json"] = json.dumps([v for _, v in visit_items])
        context["recent_logs"] = ticket_logs.select_related("user").order_by("-created_at")[:30]

    return render(request, "tickets/ticket_activity_dashboard.html", context)


@_login_required
def ticket_notifications(request):
    qs = (
        TicketNotification.objects.filter(recipient=request.user)
        .select_related("ticket", "actor")
        .order_by("-created_at")
    )
    if request.GET.get("unread") == "1":
        qs = qs.filter(is_read=False)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "tickets/ticket_notifications.html",
        {"notifications": page, "unread_count": qs.filter(is_read=False).count()},
    )


@_login_required
@require_POST
def mark_notification_read(request, pk):
    n = get_object_or_404(TicketNotification, pk=pk, recipient=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return redirect("tickets:ticket_notifications")


@_login_required
@require_POST
def mark_all_notifications_read(request):
    TicketNotification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True
    )
    return JsonResponse({"ok": True})
