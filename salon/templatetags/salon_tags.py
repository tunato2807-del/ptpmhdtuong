from django import template
register = template.Library()

@register.filter
def money(value):
    return f'{int(value or 0):,}'.replace(',', '.') + ' ₫'

@register.filter
def service_photo(name):
    """Editorial photography; never interpolates user input into a file path."""
    name = str(name).casefold()
    if 'râu' in name or 'signature' in name:
        photo = 'beard-care'
    elif 'uốn' in name:
        photo = 'hair-styling'
    elif 'gội' in name:
        photo = 'beard-care'
    elif 'combo' in name:
        photo = 'hair-styling'
    else:
        photo = 'precision-cut'
    return f'images/photos/{photo}.webp'

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    query = context['request'].GET.copy()
    for key, value in kwargs.items(): query[key] = str(value)
    return query.urlencode()
