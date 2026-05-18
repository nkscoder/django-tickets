from django import template
from django.db import DatabaseError, OperationalError

register = template.Library()


@register.simple_tag
def ticket_unread_notification_count(user):
    """Unread in-app notifications (no external services)."""
    if not user or not getattr(user, "is_authenticated", False):
        return 0
    try:
        from tickets.models import TicketNotification

        return TicketNotification.objects.filter(
            recipient=user, is_read=False
        ).count()
    except (DatabaseError, OperationalError, LookupError):
        return 0
