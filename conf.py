"""Configurable settings for the generic tickets package.

Author: Nitesh Kumar Singh (nkscoder) — https://nkscoder.in
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


DEFAULTS = {
    "BASE_TEMPLATE": "tickets/base.html",
    "LOGIN_URL": "login",
    "DB_ALIAS": "default",
    "ENABLE_ACTIVITY_DASHBOARD": False,
    "ENABLE_SIGNATERS": True,
    "LINK_TYPES": [
        ("generic", "Generic"),
        ("external", "External record"),
    ],
    "USER_SEARCH_FIELDS": ["first_name", "last_name", "email", "username"],
    "CREATE_PERMISSION": "tickets.add_ticket",
    "ADMIN_CHANGE_PERMISSION": None,
}


def get_setting(name):
    key = f"TICKETS_{name}"
    if hasattr(settings, key):
        return getattr(settings, key)
    return DEFAULTS[name]


def tickets_db_alias():
    return get_setting("DB_ALIAS")


def tickets_using():
    alias = tickets_db_alias()
    return {"using": alias} if alias != "default" else {}


def user_search_fields():
    fields = get_setting("USER_SEARCH_FIELDS")
    if not fields:
        raise ImproperlyConfigured("TICKETS_USER_SEARCH_FIELDS must not be empty.")
    return fields
