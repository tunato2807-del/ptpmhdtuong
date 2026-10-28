from django import template

register = template.Library()


@register.filter
def money(value):
    return f"{int(value or 0):,}".replace(",", ".") + " ₫"


@register.filter
def service_photo(name):
    """Editorial photography; never interpolates user input into a file path."""
    name = str(name).casefold()
    if "râu" in name:
        photo = "grooming.png"
    elif "uốn" in name:
        photo = "hair-care.jpg"
    elif "gội" in name:
        photo = "hair-wash.png"
    elif "combo" in name:
        photo = "consultation.jpg"
    else:
        photo = "precision-cut.png"
    return f"images/photos/{photo}"


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        query[key] = str(value)
    return query.urlencode()
