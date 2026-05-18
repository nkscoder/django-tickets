from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from ..models import (
    Question,
    ReportSummary,
    Ticket,
    TicketAnswer,
    TicketReassignment,
    TicketStatusHistory,
)
from ..utils import user_has_ticket_access
from .decorators import ticket_login_required

User = get_user_model()


@ticket_login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("created_by").prefetch_related("assigned_users"),
        pk=pk,
        is_deleted=False,
    )
    user = request.user

    if not user_has_ticket_access(ticket, user):
        raise PermissionDenied("You do not have access to this ticket.")

    is_creator = user.id == ticket.created_by_id
    is_assignee = ticket.assigned_users.filter(id=user.id).exists()

    user_answers = TicketAnswer.objects.filter(
        ticket=ticket, answered_by=user
    ).select_related("question")
    questions = Question.objects.filter(status="active").order_by("id")

    can_edit_ticket = (
        (is_assignee and ticket.status != "closed")
        or user.is_superuser
        or is_creator
    )

    if is_creator or user.is_superuser:
        report_summaries = ReportSummary.objects.filter(ticket=ticket).select_related(
            "user", "reassignment"
        )
    else:
        report_summaries = ReportSummary.objects.filter(ticket=ticket, user=user)

    my_report = (
        ReportSummary.objects.filter(ticket=ticket, reassignment__isnull=True, user=user)
        .order_by("-id")
        .first()
    )

    reassign_id = request.GET.get("reassign")
    reassignment = None
    if reassign_id:
        reassignment = get_object_or_404(
            TicketReassignment.objects.prefetch_related(
                "answers__question", "new_assigned_users"
            ),
            id=reassign_id,
            ticket=ticket,
        )

    status_history = TicketStatusHistory.objects.filter(ticket=ticket).order_by(
        "-created_at"
    )

    context = {
        "ticket": ticket,
        "questions": questions,
        "user_answers": user_answers,
        "can_edit_ticket": can_edit_ticket,
        "is_creator": is_creator,
        "is_assignee": is_assignee,
        "report_summaries": report_summaries,
        "my_report_message": (my_report.summary if my_report else "") or "",
        "my_report_file": my_report.file if my_report else None,
        "reassignment": reassignment,
        "status_history": status_history,
        "link_display": ticket.link_label or ticket.title,
    }
    return render(request, "tickets/ticket_detail.html", context)
