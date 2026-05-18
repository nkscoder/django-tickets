from django import template

from tickets.conf import get_setting

register = template.Library()


@register.simple_tag
def tickets_base_template():
    return get_setting("BASE_TEMPLATE")
