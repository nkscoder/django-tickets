from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from ..models import Ticket, TicketAnswer, TicketStatusHistory
from ..utils import add_status_history
from .decorators import ticket_login_required


def _user_tickets(user):
    if user.is_superuser:
        return Ticket.objects.filter(is_deleted=False)
    return Ticket.objects.filter(
        Q(created_by=user)
        | Q(assigned_users=user)
        | Q(reassignments__new_assigned_users=user),
        is_deleted=False,
    ).distinct()


@ticket_login_required
def dashboard_view(request):
    tickets = _user_tickets(request.user)
    return render(
        request,
        "tickets/dashboard.html",
        {
            "total_tickets": tickets.count(),
            "open_tickets": tickets.filter(status="open").count(),
            "closed_tickets": tickets.filter(status="closed").count(),
            "reassigned_tickets": tickets.filter(reassignments__isnull=False).distinct().count(),
        },
    )


@ticket_login_required
def view_ticket_history(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    history = TicketStatusHistory.objects.filter(ticket=ticket).order_by("created_at")
    return render(
        request,
        "tickets/ticket_history.html",
        {"ticket": ticket, "history": history},
    )


@ticket_login_required
def reopen_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    if ticket.created_by_id != request.user.id and not request.user.is_superuser:
        return JsonResponse({"responseCode": 403, "responseMessage": "Forbidden."}, status=403)

    if request.method == "POST":
        add_status_history(ticket, request.user, "reopened")
        ticket.status = "reopened"
        ticket.save(update_fields=["status", "updated_at"])
        TicketAnswer.objects.filter(ticket=ticket, is_final=True).update(is_final=False)
        return JsonResponse({"responseCode": 200, "responseMessage": "Ticket reopened."})

    return render(request, "tickets/ticket_detail.html", {"ticket": ticket})


@ticket_login_required
def submit_reopened_answers(request, ticket_id):
    from .answers import submit_all_answers

    return submit_all_answers(request, ticket_id)
