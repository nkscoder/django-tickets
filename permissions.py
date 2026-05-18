"""Permission helpers — no hard dependency on host-project apps."""

from django.contrib.auth import get_user_model

from .conf import get_setting


def can_create_ticket(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    perm = get_setting("CREATE_PERMISSION")
    if perm:
        return user.has_perm(perm)

    return user.has_perm("tickets.add_ticket")


def can_admin_modify_ticket(ticket) -> bool:
    from .models import ReassignmentAnswer, TicketAnswer

    if ticket.status == "closed":
        return False

    ticket_final = TicketAnswer.objects.filter(
        ticket=ticket, is_active=True, is_final=True
    ).exists()

    reassignment_ids = ticket.reassignments.values_list("id", flat=True)
    reassignment_final = ReassignmentAnswer.objects.filter(
        reassignment_id__in=reassignment_ids, is_active=True, is_final=True
    ).exists()

    return not (ticket_final or reassignment_final)


def user_display(user) -> str:
    if not user:
        return "-"
    first = (getattr(user, "first_name", "") or "").strip()
    last = (getattr(user, "last_name", "") or "").strip()
    name = f"{first} {last}".strip()
    if name:
        return name
    for attr in ("get_full_name", "username", "email", "phone_no"):
        val = getattr(user, attr, None)
        if callable(val):
            val = val()
        if val:
            return str(val)
    return f"User #{user.pk}"
