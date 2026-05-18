"""In-app ticket notifications only — no email, SMS, or external APIs."""

from .models import Ticket, TicketNotification


def _actor_label(user) -> str:
    if not user:
        return "Someone"
    name = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
    if name:
        return name
    if getattr(user, "phone_no", None):
        return str(user.phone_no)
    if getattr(user, "email", None):
        return str(user.email)
    return f"User #{user.pk}"


def _should_skip_recipient(*, user_id: int, actor_id: int | None) -> bool:
    """Do not notify the person who performed the action."""
    return bool(actor_id and user_id == actor_id)


def notify_ticket_assignees(*, ticket: Ticket, assignee_ids: set[int], actor=None):
    """Notify assignees when a ticket is created / users are added (not the creator)."""
    if not assignee_ids:
        return

    actor = actor or ticket.created_by
    actor_id = getattr(actor, "id", None)
    title = (ticket.title or "").strip() or f"Ticket #{ticket.id}"
    actor_name = _actor_label(actor)

    for user_id in assignee_ids:
        if _should_skip_recipient(user_id=user_id, actor_id=actor_id):
            continue

        if TicketNotification.objects.filter(
            recipient_id=user_id,
            ticket_id=ticket.id,
            notification_type=TicketNotification.NotificationType.TICKET_ASSIGNED,
            is_read=False,
        ).exists():
            continue

        TicketNotification.objects.create(
            recipient_id=user_id,
            ticket=ticket,
            actor=actor,
            notification_type=TicketNotification.NotificationType.TICKET_ASSIGNED,
            message=f"{actor_name} assigned you to ticket: {title}",
            meta={
                "ticket_id": ticket.id,
                "ticket_title": title,
                "actor_id": actor_id,
                "event": "create_or_assign",
            },
        )


def notify_ticket_reassignees(*, ticket: Ticket, assignee_ids: set[int], actor=None):
    """Notify users added on reassignment (not the person who reassigned)."""
    if not assignee_ids:
        return

    actor_id = getattr(actor, "id", None) if actor else None
    actor_name = _actor_label(actor)
    title = (ticket.title or "").strip() or f"Ticket #{ticket.id}"

    for user_id in assignee_ids:
        if _should_skip_recipient(user_id=user_id, actor_id=actor_id):
            continue

        if TicketNotification.objects.filter(
            recipient_id=user_id,
            ticket_id=ticket.id,
            notification_type=TicketNotification.NotificationType.TICKET_REASSIGNED,
            is_read=False,
        ).exists():
            continue

        TicketNotification.objects.create(
            recipient_id=user_id,
            ticket=ticket,
            actor=actor,
            notification_type=TicketNotification.NotificationType.TICKET_REASSIGNED,
            message=f"{actor_name} reassigned ticket to you: {title}",
            meta={
                "ticket_id": ticket.id,
                "ticket_title": title,
                "actor_id": actor_id,
                "event": "reassign",
            },
        )
