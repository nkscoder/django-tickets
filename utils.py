"""Generic ticket utilities — no host-project imports."""

from collections import defaultdict

from django.db.models import Count, Exists, OuterRef, Q

from .models import (
    ReassignmentAnswer,
    Ticket,
    TicketActionTrace,
    TicketAnswer,
    TicketStatusHistory,
)


def add_status_history(ticket, user, new_status):
    last = (
        TicketStatusHistory.objects.filter(ticket=ticket)
        .order_by("-created_at", "-id")
        .first()
    )
    old_status = last.new_status if last else ticket.status
    return TicketStatusHistory.objects.create(
        ticket=ticket,
        old_status=old_status,
        new_status=new_status,
        changed_by=user,
    )


def get_all_ticket_assignees(ticket):
    users_map = {}
    for u in ticket.assigned_users.all():
        users_map[u.id] = u
    for ra in ticket.reassignments.all():
        for u in ra.new_assigned_users.all():
            users_map[u.id] = u
    return list(users_map.values())


def get_ticket_reply_summary(ticket, current_user=None):
    all_assignees = get_all_ticket_assignees(ticket)
    assignee_ids = {u.id for u in all_assignees}
    ras = list(ticket.reassignments.all())
    latest_ra = ras[0] if ras else None
    received_user_ids = set()

    for ans in ticket.answers.all():
        if not ans.is_active or not ans.is_final:
            continue
        if ans.answered_by_id not in assignee_ids:
            continue
        if ans.answer and str(ans.answer).strip():
            received_user_ids.add(ans.answered_by_id)

    for ra in ras:
        for ans in ra.answers.all():
            if not ans.is_active or not ans.is_final:
                continue
            if ans.answered_by_id not in assignee_ids:
                continue
            if ans.answer and str(ans.answer).strip():
                received_user_ids.add(ans.answered_by_id)

    my_answered = bool(current_user and current_user.id in received_user_ids)
    return {
        "all_assignees": all_assignees,
        "received_user_ids": received_user_ids,
        "latest_ra": latest_ra,
        "my_answered": my_answered,
    }


def build_ticket_reply_index(ticket_ids, current_user_id=None):
    if not ticket_ids:
        return {}

    reassignment_model = Ticket.reassignments.rel.related_model
    assignee_map = defaultdict(set)
    received_map = defaultdict(set)

    for ticket_id, user_id in Ticket.objects.filter(id__in=ticket_ids).values_list(
        "id", "assigned_users__id"
    ):
        if user_id:
            assignee_map[ticket_id].add(user_id)

    for ticket_id, user_id in reassignment_model.objects.filter(
        ticket_id__in=ticket_ids
    ).values_list("ticket_id", "new_assigned_users__id"):
        if user_id:
            assignee_map[ticket_id].add(user_id)

    for ticket_id, answered_by_id, answer_text in TicketAnswer.objects.filter(
        ticket_id__in=ticket_ids, is_active=True, is_final=True
    ).values_list("ticket_id", "answered_by_id", "answer"):
        if answered_by_id and answer_text and str(answer_text).strip():
            received_map[ticket_id].add(answered_by_id)

    for ticket_id, answered_by_id, answer_text in ReassignmentAnswer.objects.filter(
        reassignment__ticket_id__in=ticket_ids, is_active=True, is_final=True
    ).values_list("reassignment__ticket_id", "answered_by_id", "answer"):
        if answered_by_id and answer_text and str(answer_text).strip():
            received_map[ticket_id].add(answered_by_id)

    result = {}
    for ticket_id in ticket_ids:
        assignee_ids = assignee_map.get(ticket_id, set())
        valid_received = received_map.get(ticket_id, set()).intersection(assignee_ids)
        expected_count = len(assignee_ids)
        received_count = len(valid_received)
        result[ticket_id] = {
            "expected_count": expected_count,
            "received_count": received_count,
            "is_received": expected_count > 0 and received_count >= expected_count,
            "is_partial_received": 0 < received_count < expected_count,
            "my_answered": bool(current_user_id and current_user_id in valid_received),
        }
    return result


def filter_ticket_ids_by_scope(ticket_qs, scope, created_bucket, my_bucket, user):
    if not scope:
        return None

    if scope == "created":
        created_qs = ticket_qs if user.is_superuser else ticket_qs.filter(created_by=user)
        rows = list(created_qs.values("id", "status"))
        reply_index = build_ticket_reply_index([r["id"] for r in rows], user.id)
        ids = []
        for row in rows:
            tid, status = row["id"], row["status"]
            summary = reply_index.get(tid, {})
            if created_bucket == "total":
                ids.append(tid)
            elif created_bucket == "pending" and status != "closed" and not summary.get("is_received"):
                ids.append(tid)
            elif created_bucket == "received" and status != "closed" and summary.get("is_received"):
                ids.append(tid)
            elif created_bucket == "closed" and status == "closed":
                ids.append(tid)
            elif created_bucket == "reopened" and status == "reopened":
                ids.append(tid)
        return ids

    if scope == "my":
        my_qs = (
            ticket_qs
            if user.is_superuser
            else ticket_qs.filter(
                Q(assigned_users=user) | Q(reassignments__new_assigned_users=user)
            ).distinct()
        )
        rows = list(my_qs.values("id", "status"))
        ticket_ids = [r["id"] for r in rows]
        reply_index = build_ticket_reply_index(ticket_ids, user.id)
        my_action_ids = set(
            TicketActionTrace.objects.filter(
                ticket_id__in=ticket_ids,
                action_key="ACTION_TAKEN",
                is_success=True,
                performed_by=user,
            ).values_list("ticket_id", flat=True)
        )
        ids = []
        for row in rows:
            tid, status = row["id"], row["status"]
            summary = reply_index.get(tid, {})
            has_answer = summary.get("my_answered")
            has_action = tid in my_action_ids
            if my_bucket == "total":
                ids.append(tid)
            elif my_bucket == "new" and status != "closed" and not has_answer and not has_action:
                ids.append(tid)
            elif my_bucket == "pending" and status != "closed" and (has_answer or has_action):
                ids.append(tid)
            elif my_bucket == "closed" and status == "closed":
                ids.append(tid)
        return ids

    return None


def user_has_ticket_access(ticket, user):
    if user.is_superuser:
        return True
    if ticket.created_by_id == user.id:
        return True
    if ticket.assigned_users.filter(id=user.id).exists():
        return True
    if ticket.reassignments.filter(new_assigned_users=user).exists():
        return True
    return False


def annotate_ticket_list_row(ticket, user):
    """Attach display fields used by ticket_list template."""
    summary = get_ticket_reply_summary(ticket, current_user=user)
    all_assignees = summary["all_assignees"]
    received = summary["received_user_ids"]

    if user.is_superuser or ticket.created_by_id == user.id:
        ticket.current_assignees = all_assignees
        expected = len(all_assignees)
        received_count = len(received)
    else:
        ticket.current_assignees = [u for u in all_assignees if u.id == user.id]
        expected = 1 if ticket.current_assignees else 0
        received_count = 1 if summary["my_answered"] else 0

    if user.is_superuser or ticket.created_by_id == user.id:
        if expected and received_count >= expected:
            ticket.answer_status = "Received"
        elif received_count:
            ticket.answer_status = f"Partial ({received_count}/{expected})"
        else:
            ticket.answer_status = "Pending"
    else:
        ticket.answer_status = "Replied" if summary["my_answered"] else "Pending"

    ras = list(ticket.reassignments.all())
    latest_ra = ras[0] if ras else None
    ticket.latest_ra_id = latest_ra.id if latest_ra else None
    ticket.link_display = ticket.link_label or ticket.title
