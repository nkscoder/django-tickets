from functools import wraps

from django.contrib.auth.decorators import login_required as django_login_required

from tickets.conf import get_setting


def ticket_login_required(view_func):
    return django_login_required(login_url=get_setting("LOGIN_URL"))(view_func)
