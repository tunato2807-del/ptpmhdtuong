from django.conf import settings

def brand(request):
    return {'brand_name': 'GENTLEMAN', 'demo_mode': settings.DEBUG,
            'nav_section': request.resolver_match.url_name if request.resolver_match else ''}
