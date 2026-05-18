import json

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.shortcuts import render
from django.utils.dateparse import parse_date

from tickets.permissions import can_create_ticket

from ..models import (
    Category,
    Question,
    ReassignmentAnswer,
    ReportSummary,
    Ticket,
    TicketActionTrace,
    TicketAnswer,
)
from ..utils import annotate_ticket_list_row, filter_ticket_ids_by_scope
from .decorators import ticket_login_required


@ticket_login_required
def ticket_list(request):
    user = request.user
    params = request.GET.copy()
    params.pop("page", None)
    preserved_qs = params.urlencode()

    reassignment_model = Ticket.reassignments.rel.related_model
    report_exists_sq = ReportSummary.objects.filter(ticket_id=OuterRef("pk"))

    if user.is_superuser:
        base_qs = Ticket.objects.all()
    else:
        base_qs = Ticket.objects.filter(
            Q(created_by=user)
            | Q(assigned_users=user)
            | Q(reassignments__new_assigned_users=user)
        ).distinct()

    qs = (
        base_qs.filter(is_deleted=False)
        .select_related("created_by")
        .annotate(has_report=Exists(report_exists_sq))
        .order_by("-created_at", "-id")
    )

    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "all").strip() or "all"
    link_type_filter = request.GET.get("link_type", "").strip()
    from_date = parse_date(request.GET.get("from_date", "").strip() or "")
    to_date = parse_date(request.GET.get("to_date", "").strip() or "")

    scope = request.GET.get("scope", "").strip()
    created_bucket = request.GET.get("created_bucket", "").strip()
    my_bucket = request.GET.get("my_bucket", "").strip()

    if search_query:
        if search_query.isdigit():
            qs = qs.filter(Q(id=int(search_query)) | Q(title__icontains=search_query))
        else:
            qs = qs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(link_label__icontains=search_query)
                | Q(file_no__icontains=search_query)
                | Q(status__icontains=search_query)
                | Q(created_by__first_name__icontains=search_query)
                | Q(created_by__last_name__icontains=search_query)
            ).distinct()

    if status_filter != "all":
        if status_filter == "reassigned":
            qs = qs.filter(reassignments__isnull=False).distinct()
        else:
            qs = qs.filter(status=status_filter)

    if link_type_filter:
        qs = qs.filter(link_type__icontains=link_type_filter)

    if from_date:
        qs = qs.filter(created_at__date__gte=from_date)
    if to_date:
        qs = qs.filter(created_at__date__lte=to_date)

    filtered_ids = filter_ticket_ids_by_scope(qs, scope, created_bucket, my_bucket, user)
    if filtered_ids is not None:
        qs = qs.filter(id__in=filtered_ids) if filtered_ids else qs.none()

    dashboard_qs = qs
    total_tickets = dashboard_qs.count()
    open_tickets = dashboard_qs.filter(status="open").count()
    closed_tickets = dashboard_qs.filter(status="closed").count()
    reopened_tickets = dashboard_qs.filter(status="reopened").count()
    reassigned_tickets = dashboard_qs.filter(reassignments__isnull=False).distinct().count()

    page_size = int(request.GET.get("page_size", 10) or 10)
    if page_size not in (10, 20, 50, 100):
        page_size = 10

    paginator = Paginator(qs, page_size)
    page_num = request.GET.get("page", 1)
    try:
        tickets_page = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        tickets_page = paginator.page(1)

    page_ids = [t.id for t in tickets_page.object_list]
    page_qs = (
        Ticket.objects.filter(id__in=page_ids)
        .select_related("created_by")
        .prefetch_related(
            "assigned_users",
            Prefetch("answers", queryset=TicketAnswer.objects.filter(is_active=True)),
            Prefetch(
                "reassignments",
                queryset=reassignment_model.objects.order_by("-created_at").prefetch_related(
                    "new_assigned_users",
                    Prefetch(
                        "answers",
                        queryset=ReassignmentAnswer.objects.filter(is_active=True),
                    ),
                ),
            ),
        )
    )
    ticket_map = {t.id: t for t in page_qs}
    ordered = [ticket_map[i] for i in page_ids if i in ticket_map]

    for ticket in ordered:
        annotate_ticket_list_row(ticket, user)

    tickets_page.object_list = ordered

    questions = list(Question.objects.filter(status="active").order_by("id").values("id", "text"))
    categories = list(Category.objects.all().order_by("id").values("id", "name"))

    return render(
        request,
        "tickets/ticket_list_core.html",
        {
            "tickets": tickets_page,
            "questions": json.dumps(questions),
            "categories": categories,
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "closed_tickets": closed_tickets,
            "reopened_tickets": reopened_tickets,
            "reassigned_tickets": reassigned_tickets,
            "search_query": search_query,
            "status_filter": status_filter,
            "link_type_filter": link_type_filter,
            "from_date": request.GET.get("from_date", ""),
            "to_date": request.GET.get("to_date", ""),
            "page_size": page_size,
            "preserved_qs": preserved_qs,
            "create_ticket": can_create_ticket(user),
            "user": user,
            "scope": scope,
            "created_bucket": created_bucket,
            "my_bucket": my_bucket,
        },
    )
