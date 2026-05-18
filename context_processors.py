from .conf import get_setting


def tickets_settings(request):
    return {
        "TICKETS_BASE_TEMPLATE": get_setting("BASE_TEMPLATE"),
        "TICKETS_ENABLE_SIGNATERS": get_setting("ENABLE_SIGNATERS"),
    }
