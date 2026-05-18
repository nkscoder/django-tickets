import json

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from ..models import (
    ReassignmentAnswer,
    ReportSummary,
    Ticket,
    TicketAnswer,
    TicketLog,
    TicketReassignment,
    TicketStatusHistory,
)
from ..utils import add_status_history, user_has_ticket_access
from .decorators import ticket_login_required

User = get_user_model()


@ticket_login_required
def reassign_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method != "POST":
        return JsonResponse({"responseCode": 405, "responseMessage": "POST required."})

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return JsonResponse(
            {"responseCode": 400, "responseMessage": f"Invalid JSON: {exc}"}
        )

    user_id = data.get("user")
    reason = data.get("reason", "")

    if not user_id:
        return JsonResponse(
            {"responseCode": 400, "responseMessage": "Select a user to reassign."}
        )

    try:
        assigned_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse(
            {"responseCode": 404, "responseMessage": "User not found."}
        )

    with transaction.atomic():
        reassignment = TicketReassignment.objects.create(
            ticket=ticket,
            reassigned_by=request.user,
            reason=reason,
        )
        reassignment.new_assigned_users.add(assigned_user)

        for t_ans in TicketAnswer.objects.filter(ticket=ticket):
            ReassignmentAnswer.objects.update_or_create(
                reassignment=reassignment,
                question=t_ans.question,
                answered_by=t_ans.answered_by,
                defaults={"is_active": True, "is_final": False},
            )

        add_status_history(ticket, request.user, "reassigned")

    return JsonResponse(
        {
            "responseCode": 200,
            "responseMessage": f"Ticket reassigned to {assigned_user}.",
        }
    )


@ticket_login_required
def reassign_ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user = request.user
    all_ra = TicketReassignment.objects.filter(ticket=ticket).prefetch_related(
        "new_assigned_users", "reassigned_by"
    )

    if user == ticket.created_by or user.is_superuser:
        reassignments = all_ra
    else:
        reassignments = all_ra.filter(
            new_assigned_users=user
        ) | all_ra.filter(reassigned_by=user)

    return render(
        request,
        "tickets/reassign_ticket_detail.html",
        {"ticket": ticket, "reassignments": reassignments.distinct()},
    )


@ticket_login_required
def reassign_detail_view(request, ticket_id, reassign_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    reassignment = get_object_or_404(
        TicketReassignment.objects.prefetch_related("answers__question", "new_assigned_users"),
        id=reassign_id,
        ticket=ticket,
    )

    if not user_has_ticket_access(ticket, request.user):
        raise PermissionDenied()

    status_history = TicketStatusHistory.objects.filter(ticket=ticket).order_by("-created_at")
    logs = TicketLog.objects.filter(ticketReassignment=reassignment).select_related("user")

    return render(
        request,
        "tickets/reassign_single_detail.html",
        {
            "ticket": ticket,
            "reassignment": reassignment,
            "answers": reassignment.answers.all(),
            "logs": logs,
            "status_history": status_history,
        },
    )


@ticket_login_required
def submit_reassign_form(request, reassign_id):
    reassignment = get_object_or_404(TicketReassignment, id=reassign_id)
    ticket = reassignment.ticket

    if request.method != "POST":
        return JsonResponse({"responseCode": 405, "responseMessage": "POST required."})

    user = request.user
    action = (request.POST.get("action") or "draft").strip().lower()

    for key, value in request.POST.items():
        if not key.startswith("answer_"):
            continue
        qid = key.replace("answer_", "")
        text = (value or "").strip()
        if not text:
            continue
        ra, _ = ReassignmentAnswer.objects.get_or_create(
            reassignment=reassignment,
            question_id=qid,
            answered_by=user,
            defaults={"is_active": True},
        )
        ra.answer = text
        ra.is_final = action == "final"
        ra.save()

    if action == "final":
        add_status_history(ticket, user, "submitted")

    return JsonResponse({"responseCode": 200, "responseMessage": "Reassignment answers saved."})


@ticket_login_required
def update_ticket_status(request, ticket_id):
    if request.method != "POST":
        return JsonResponse({"responseCode": 405, "responseMessage": "POST required."})

    ticket = get_object_or_404(Ticket, id=ticket_id)
    new_status = request.POST.get("status", "").strip()
    if new_status not in dict(Ticket.STATUS_CHOICES):
        return JsonResponse({"responseCode": 400, "responseMessage": "Invalid status."})

    add_status_history(ticket, request.user, new_status)
    ticket.status = new_status
    if new_status == "closed":
        ticket.closed_by = request.user
    ticket.save(update_fields=["status", "closed_by", "updated_at"])

    return JsonResponse({"responseCode": 200, "responseMessage": "Status updated."})
