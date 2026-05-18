from django.db.models import Max
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from tickets.conf import get_setting

from ..models import (
    Question,
    ReportSummary,
    Signater,
    Ticket,
    TicketAnswer,
    TicketQuestionHistory,
    TicketSignater,
)
from ..utils import add_status_history
from .decorators import ticket_login_required


@ticket_login_required
def submit_answer(request, ticket_id, question_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method")

    answer_text = request.POST.get("answer", "").strip()
    if not answer_text:
        return JsonResponse(
            {"responseCode": 400, "responseMessage": "Answer cannot be empty."}
        )

    try:
        ticket_answer = TicketAnswer.objects.get(
            ticket_id=ticket_id,
            question_id=question_id,
            answered_by=request.user,
        )
        old = ticket_answer.answer
        ticket_answer.answer = answer_text
        ticket_answer.save()
        if old != answer_text:
            TicketQuestionHistory.objects.create(
                ticket_answer=ticket_answer,
                old_answer=old,
                changed_by=request.user,
            )
        return JsonResponse(
            {
                "responseCode": 200,
                "responseMessage": "Answer saved.",
                "answer": answer_text,
                "question_id": question_id,
            }
        )
    except TicketAnswer.DoesNotExist:
        return JsonResponse(
            {"responseCode": 404, "responseMessage": "Answer slot not found."}
        )


@ticket_login_required
def submit_ticket_form(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method != "POST":
        return JsonResponse({"responseCode": 405, "responseMessage": "POST required."})

    user = request.user
    action = (request.POST.get("action") or "draft").strip().lower()
    answers_data = {}

    for key, value in request.POST.items():
        if not key.startswith("answer_"):
            continue
        question_id = key.replace("answer_", "")
        answer_text = (value or "").strip()
        if not answer_text:
            continue

        qs = TicketAnswer.objects.filter(
            ticket=ticket, question_id=question_id, answered_by=user
        )
        editable = qs.filter(is_final=False).order_by("-version").first()
        max_version = qs.aggregate(Max("version"))["version__max"] or 0

        if editable:
            ta = editable
        else:
            ta = TicketAnswer(
                ticket=ticket,
                question_id=question_id,
                answered_by=user,
                version=max_version + 1,
            )

        ta.answer = answer_text
        ta.is_final = action == "final"
        ta.is_active = action == "final"
        ta.save()
        answers_data[question_id] = ta.answer

    if get_setting("ENABLE_SIGNATERS"):
        for action_type, post_key in (("to", "signaters_to"), ("from", "signaters_from")):
            sid = (request.POST.get(post_key) or "").strip()
            if sid:
                signater = Signater.objects.filter(pk=sid).first()
                if signater:
                    TicketSignater.objects.update_or_create(
                        ticket=ticket,
                        user=user,
                        action_type=action_type,
                        defaults={"signater": signater},
                    )
            else:
                TicketSignater.objects.filter(
                    ticket=ticket, user=user, action_type=action_type
                ).delete()

    message = request.POST.get("message", "").strip()
    files = request.FILES.getlist("files")
    report_obj = (
        ReportSummary.objects.filter(ticket=ticket, reassignment__isnull=True, user=user)
        .order_by("-id")
        .first()
    )
    if message or files:
        if not report_obj:
            report_obj = ReportSummary(ticket=ticket, user=user)
        if message:
            report_obj.summary = message
        if files:
            report_obj.file = files[0]
        report_obj.save()

    msg = "Draft saved." if action == "draft" else "Submitted successfully."
    if action == "final":
        add_status_history(ticket, user, "submitted")
        return JsonResponse(
            {
                "responseCode": 200,
                "responseMessage": msg,
                "answers": answers_data,
                "redirect_url": reverse("tickets:ticket_success", args=[ticket.id]),
            }
        )

    return JsonResponse(
        {
            "responseCode": 200,
            "responseMessage": msg,
            "answers": answers_data,
        }
    )


@ticket_login_required
def submit_all_answers(request, ticket_id):
    if request.method != "POST":
        return JsonResponse({"responseCode": 405, "responseMessage": "POST required."})

    ticket = get_object_or_404(Ticket, id=ticket_id)
    count = 0
    for key, value in request.POST.items():
        if key.startswith("answer_") and value.strip():
            qid = key.replace("answer_", "")
            TicketAnswer.objects.filter(
                ticket=ticket, question_id=qid, answered_by=request.user, is_final=False
            ).update(answer=value.strip(), is_final=True, is_active=True)
            count += 1

    return JsonResponse(
        {"responseCode": 200, "responseMessage": f"Saved {count} answer(s)."}
    )


@ticket_login_required
def get_ticket_history(request, ticket_id):
    from ..models import TicketQuestionHistory

    history = TicketQuestionHistory.objects.filter(
        ticket_answer__ticket_id=ticket_id
    ).select_related("ticket_answer__question", "changed_by")

    data = [
        {
            "question": h.ticket_answer.question.text,
            "old_answer": h.old_answer,
            "changed_by": str(h.changed_by) if h.changed_by else None,
            "reason": h.reason,
            "changed_at": h.changed_at.strftime("%Y-%m-%d %H:%M"),
        }
        for h in history
    ]
    return JsonResponse({"history": data})
