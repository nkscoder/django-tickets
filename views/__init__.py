"""Layer A — generic ticket views."""

from .answers import (
    get_ticket_history,
    submit_all_answers,
    submit_answer,
    submit_ticket_form,
)
from .api import (
    TicketCreateAPIView,
    UserSearchAPIView,
    get_questions_by_category,
    get_users_by_query,
)
from .crud import (
    create_ticket,
    delete_ticket,
    edit_ticket,
    store_ticket,
    ticket_success,
    update_ticket,
)
from .dashboard import (
    dashboard_view,
    reopen_ticket,
    submit_reopened_answers,
    view_ticket_history,
)
from .detail import ticket_detail
from .list import ticket_list
from .reassign import (
    reassign_detail_view,
    reassign_ticket,
    reassign_ticket_detail,
    submit_reassign_form,
    update_ticket_status,
)

__all__ = [
    "ticket_list",
    "create_ticket",
    "store_ticket",
    "ticket_detail",
    "ticket_success",
    "edit_ticket",
    "update_ticket",
    "delete_ticket",
    "reassign_ticket",
    "reassign_ticket_detail",
    "reassign_detail_view",
    "submit_reassign_form",
    "submit_answer",
    "submit_ticket_form",
    "submit_all_answers",
    "update_ticket_status",
    "get_ticket_history",
    "get_questions_by_category",
    "get_users_by_query",
    "UserSearchAPIView",
    "TicketCreateAPIView",
    "dashboard_view",
    "view_ticket_history",
    "reopen_ticket",
    "submit_reopened_answers",
]
