from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Dict lookup by key for templates: {{ mapping|get_item:key }}."""
    if mapping is None:
        return None
    return mapping.get(key)
