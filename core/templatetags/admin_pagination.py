from django import template
from django.contrib.admin.templatetags.admin_list import PAGE_VAR

register = template.Library()


@register.simple_tag
def admin_page_url(cl, page_number):
    return cl.get_query_string({PAGE_VAR: page_number})
