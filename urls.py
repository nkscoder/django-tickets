from django.urls import path

from . import ticket_activity_views
from .views import (
    TicketCreateAPIView,
    UserSearchAPIView,
    create_ticket,
    dashboard_view,
    delete_ticket,
    edit_ticket,
    get_questions_by_category,
    get_ticket_history,
    get_users_by_query,
    reopen_ticket,
    reassign_detail_view,
    reassign_ticket,
    reassign_ticket_detail,
    store_ticket,
    submit_all_answers,
    submit_answer,
    submit_reassign_form,
    submit_reopened_answers,
    submit_ticket_form,
    ticket_detail,
    ticket_list,
    ticket_success,
    update_ticket,
    update_ticket_status,
    view_ticket_history,
)

app_name = "tickets"

urlpatterns = [
    path("", ticket_list, name="ticket_list"),
    path("ticket_list/", ticket_list, name="ticket_list_alt"),
    path("create_ticket/", create_ticket, name="create_ticket"),
    path("create_ticket/store-create/", store_ticket, name="store_ticket"),
    path("ticket_detail/<int:pk>/", ticket_detail, name="ticket_detail"),
    path("ticket/success/<int:ticket_id>/", ticket_success, name="ticket_success"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("history/<int:ticket_id>/", get_ticket_history, name="ticket_history"),
    path("tickets/<int:ticket_id>/history/", view_ticket_history, name="view_ticket_history"),
    path("reopen/<int:ticket_id>/", reopen_ticket, name="reopen_ticket"),
    path(
        "reopen/<int:ticket_id>/submit-answers/",
        submit_reopened_answers,
        name="submit_reopened_answers",
    ),
    path("update-status/<int:ticket_id>/", update_ticket_status, name="update_status"),
    path("delete/<int:pk>/", delete_ticket, name="delete_ticket"),
    path("edit/<int:pk>/", edit_ticket, name="edit_ticket"),
    path("update/<int:pk>/", update_ticket, name="update_ticket"),
    path("reassign_ticket/<int:ticket_id>/", reassign_ticket, name="reassign_ticket"),
    path(
        "tickets/<int:pk>/reassign-detail/",
        reassign_ticket_detail,
        name="reassign_ticket_detail",
    ),
    path(
        "tickets/<int:ticket_id>/reassign/<int:reassign_id>/detail/",
        reassign_detail_view,
        name="reassign_single_detail",
    ),
    path(
        "reassign/submit/<int:reassign_id>/",
        submit_reassign_form,
        name="submit_reassign_form",
    ),
    path(
        "tickets/<int:ticket_id>/submit_answer/<int:question_id>/",
        submit_answer,
        name="submit_answer",
    ),
    path(
        "tickets/<int:ticket_id>/submit-all/",
        submit_all_answers,
        name="submit_all_answers",
    ),
    path(
        "<int:ticket_id>/submit_all_answers/",
        submit_all_answers,
        name="submit_all_answers_alt",
    ),
    path(
        "tickets/<int:ticket_id>/submit-form/",
        submit_ticket_form,
        name="submit_ticket_form",
    ),
    path("api/users/", UserSearchAPIView.as_view(), name="user-list-search"),
    path("api/users/search/", get_users_by_query, name="users-search"),
    path("api/questions/", get_questions_by_category, name="api_questions"),
    path("api/tickets/", TicketCreateAPIView.as_view(), name="api-ticket-create"),
    # Notifications & activity (activity app optional)
    path(
        "activity/",
        ticket_activity_views.ticket_activity_dashboard,
        name="ticket_activity_dashboard",
    ),
    path(
        "notifications/",
        ticket_activity_views.ticket_notifications,
        name="ticket_notifications",
    ),
    path(
        "notifications/<int:pk>/read/",
        ticket_activity_views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/read-all/",
        ticket_activity_views.mark_all_notifications_read,
        name="mark_all_notifications_read",
    ),
]
