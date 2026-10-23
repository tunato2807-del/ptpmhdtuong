from django import template
register = template.Library()

@register.filter
def money(value):
    return f'{int(value or 0):,}'.replace(',', '.') + ' ₫'

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    query = context['request'].GET.copy()
    for key, value in kwargs.items(): query[key] = str(value)
    return query.urlencode()
