import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tickets.conf import get_setting
from tickets.permissions import can_admin_modify_ticket, can_create_ticket

from ..forms import TicketForm
from ..models import (
    Category,
    Question,
    Signater,
    Ticket,
    TicketActionTrace,
    TicketAnswer,
    TicketLog,
    TicketStatusHistory,
)
from ..utils import add_status_history
from .decorators import ticket_login_required

User = get_user_model()


def _parse_store_payload(request):
    if request.content_type and "multipart" in request.content_type:
        users_raw = request.POST.get("users") or "[]"
        try:
            users = json.loads(users_raw)
        except json.JSONDecodeError:
            users = []
        return {
            "title": (request.POST.get("title") or "").strip(),
            "description": request.POST.get("description") or "",
            "link_type": request.POST.get("link_type") or "generic",
            "link_id": request.POST.get("link_id") or "",
            "link_label": request.POST.get("link_label") or "",
            "file_no": request.POST.get("file_no") or "",
            "users": users,
        }
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


@ticket_login_required
def create_ticket(request):
    if not can_create_ticket(request.user):
        return HttpResponseForbidden("You do not have permission to create tickets.")

    categories = list(Category.objects.all().order_by("id").values("id", "name", "description"))
    questions = list(Question.objects.filter(status="active").order_by("id").values("id", "text"))
    signaters = []
    if get_setting("ENABLE_SIGNATERS"):
        signaters = list(Signater.objects.filter(status="active").order_by("id").values("id", "ranks"))

    last = Ticket.objects.order_by("-id").values_list("id", flat=True).first()
    next_ticket_id = (last or 0) + 1

    return render(
        request,
        "tickets/create_ticket_core.html",
        {
            "form": TicketForm(),
            "categories": categories,
            "questions": questions,
            "signaters": signaters,
            "next_ticket_id": next_ticket_id,
            "link_types": get_setting("LINK_TYPES"),
        },
    )


@ticket_login_required
@require_POST
def store_ticket(request):
    if not can_create_ticket(request.user):
        return JsonResponse({"responseCode": 403, "responseMessage": "Permission denied."}, status=403)

    data = _parse_store_payload(request)
    title = data.get("title") or f"Ticket #{data.get('next_ticket_id', '')}".strip() or "Untitled"
    description = data.get("description", "")
    users = data.get("users") or []
    assignee_ids = data.get("assignee_ids") or [u.get("user_id") for u in users if u.get("user_id")]

    if not assignee_ids:
        return JsonResponse(
            {"responseCode": 400, "responseMessage": "Assign at least one user."},
            status=400,
        )

    try:
        with transaction.atomic():
            ticket = Ticket.objects.create(
                title=title,
                description=description,
                created_by=request.user,
                link_type=data.get("link_type") or "generic",
                link_id=str(data.get("link_id") or ""),
                link_label=data.get("link_label") or title,
                file_no=data.get("file_no") or "",
                status="open",
            )

            TicketActionTrace.objects.create(
                ticket=ticket,
                action_key="TICKET_CREATED",
                is_success=True,
                status_text="Ticket created",
                performed_by=request.user,
            )

            question_ids_global = data.get("question_ids") or []

            for uid in assignee_ids:
                try:
                    assigned_user = User.objects.get(pk=uid)
                except User.DoesNotExist:
                    continue
                ticket.assigned_users.add(assigned_user)
                TicketLog.objects.create(ticket=ticket, user=assigned_user, message="Assigned")

                q_ids = question_ids_global
                for u in users:
                    if str(u.get("user_id")) == str(uid):
                        q_ids = u.get("questions") or q_ids
                        break

                for qid in q_ids:
                    try:
                        q_obj = Question.objects.get(pk=int(qid))
                    except (ValueError, Question.DoesNotExist):
                        continue
                    TicketAnswer.objects.get_or_create(
                        ticket=ticket,
                        question=q_obj,
                        answered_by=assigned_user,
                        defaults={"version": 1},
                    )

            TicketStatusHistory.objects.create(
                ticket=ticket,
                old_status=None,
                new_status="open",
                changed_by=request.user,
            )

        return JsonResponse(
            {
                "responseCode": 200,
                "responseMessage": "Ticket created successfully.",
                "ticket_id": ticket.id,
            }
        )
    except Exception as exc:
        return JsonResponse(
            {"responseCode": 400, "responseMessage": str(exc)},
            status=400,
        )


@ticket_login_required
def ticket_success(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    return render(request, "tickets/ticket_success.html", {"ticket": ticket})


@ticket_login_required
@require_POST
def delete_ticket(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({"responseCode": 403, "responseMessage": "Forbidden."}, status=403)

    ticket = get_object_or_404(Ticket.all_objects, pk=pk, is_deleted=False)
    if not can_admin_modify_ticket(ticket):
        return JsonResponse(
            {
                "responseCode": 400,
                "responseMessage": "Only fresh tickets can be deleted.",
            },
            status=400,
        )

    ticket.soft_delete(user=request.user)
    return JsonResponse({"responseCode": 200, "responseMessage": "Ticket deleted."})


@ticket_login_required
def edit_ticket(request, pk):
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponseForbidden("You do not have permission to edit tickets.")

    ticket = get_object_or_404(Ticket.all_objects, pk=pk, is_deleted=False)
    if not can_admin_modify_ticket(ticket):
        messages.error(request, "This ticket can no longer be edited.")
        return redirect("tickets:ticket_list")

    return render(
        request,
        "tickets/edit_ticket_core.html",
        {"ticket": ticket, "form": TicketForm(instance=ticket)},
    )


@ticket_login_required
@require_POST
def update_ticket(request, pk):
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({"responseCode": 403, "responseMessage": "Forbidden."}, status=403)

    ticket = get_object_or_404(Ticket.all_objects, pk=pk, is_deleted=False)
    if not can_admin_modify_ticket(ticket):
        return JsonResponse(
            {"responseCode": 400, "responseMessage": "Ticket cannot be updated."},
            status=400,
        )

    data = _parse_store_payload(request)
    if not data and request.POST:
        data = {
            "title": request.POST.get("title"),
            "description": request.POST.get("description"),
            "link_type": request.POST.get("link_type"),
            "link_id": request.POST.get("link_id"),
            "file_no": request.POST.get("file_no"),
        }
    ticket.title = data.get("title") or ticket.title
    ticket.description = data.get("description", ticket.description)
    ticket.link_type = data.get("link_type") or ticket.link_type
    ticket.link_id = data.get("link_id") or ticket.link_id
    ticket.file_no = data.get("file_no") or ticket.file_no
    if data.get("title"):
        ticket.link_label = data.get("title")
    ticket.save()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or (
        request.content_type and "json" in request.content_type
    ):
        return JsonResponse({"responseCode": 200, "responseMessage": "Ticket updated."})
    messages.success(request, "Ticket updated.")
    return redirect("tickets:ticket_detail", pk=ticket.pk)
