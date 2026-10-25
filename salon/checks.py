"""Stop early when a partial source copy is missing required interface files."""
from django.contrib.staticfiles import finders
from django.core.checks import Error, Tags, register

REQUIRED_ASSETS = (
    'css/app.css', 'css/customer.css', 'css/management.css', 'css/typography.css',
    'js/app.js', 'js/customer.js',
    *(f'fonts/be-vietnam-pro-{subset}-{weight}-normal.woff2'
      for subset in ('latin', 'latin-ext', 'vietnamese')
      for weight in (400, 500, 600, 700, 800)),
)


@register(Tags.staticfiles)
def required_interface_assets(app_configs, **kwargs):
    return [Error(
        f'Thiếu file giao diện: static/{name}',
        hint='Copy đủ file từ GitHub vào đúng đường dẫn, rồi chạy collectstatic --noinput.',
        id='salon.E001',
    ) for name in REQUIRED_ASSETS if not finders.find(name)]
