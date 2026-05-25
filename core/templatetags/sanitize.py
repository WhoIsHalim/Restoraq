from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

try:
    import bleach
except ImportError:  # pragma: no cover
    bleach = None

register = template.Library()

ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "span",
    "a",
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "span": ["style"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]


@register.filter(name="sanitize_html")
def sanitize_html(value: str) -> str:
    if value is None:
        return ""
    if bleach is None:
        return str(value)
    cleaned = bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned = bleach.linkify(cleaned, parse_email=True)
    return mark_safe(cleaned)
