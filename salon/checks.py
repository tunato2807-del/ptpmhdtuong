"""Stop early when a partial source copy is missing required interface files."""

from django.contrib.staticfiles import finders
from django.core.checks import Error, Tags, register

REQUIRED_ASSETS = (
    "css/app.css",
    "css/customer.css",
    "css/management.css",
    "css/typography.css",
    "css/editorial-fonts.css",
    "css/editorial.css",
    "css/business.css",
    "js/app.js",
    "js/customer.js",
    "css/motion.css",
    "js/motion.js",
    *(
        f"fonts/be-vietnam-pro-{subset}-{weight}-normal.woff2"
        for subset in ("latin", "latin-ext", "vietnamese")
        for weight in (400, 500, 600, 700, 800)
    ),
    "fonts/lora-500-italic.woff2",
    "fonts/barlow-condensed-600-normal.woff2",
    *(
        f"images/photos/{name}"
        for name in (
            "consultation.jpg",
            "salon-lounge.jpg",
            "salon-interior.jpg",
            "hair-care.jpg",
            "precision-cut.png",
            "grooming.png",
            "hair-wash.png",
        )
    ),
)


@register(Tags.staticfiles)
def required_interface_assets(app_configs, **kwargs):
    return [
        Error(
            f"Thiếu file giao diện: static/{name}",
            hint="Copy đủ file từ GitHub vào đúng đường dẫn, rồi chạy collectstatic --noinput.",
            id="salon.E001",
        )
        for name in REQUIRED_ASSETS
        if not finders.find(name)
    ]


# Explicit inventory: missing files must still be detected after a partial copy.
REQUIRED_TEMPLATES = (
    "business/activation.html",
    "business/workspace.html",
    "business/form.html",
    "business/stylist.html",
    "base.html",
    "403.html",
    "404.html",
    "auth/login.html",
    "auth/register.html",
    "partials/form_fields.html",
    "partials/icon_arrow.html",
    "partials/messages.html",
    "partials/pagination.html",
    "public/home.html",
    "public/booking.html",
    "public/profile.html",
    "public/my_appointments.html",
    "public/appointment_detail.html",
    "public/invoice.html",
    "staff/base.html",
    "staff/dashboard.html",
    "staff/settings.html",
    "staff/resource_list.html",
    "staff/resource_form.html",
    "staff/resource_delete.html",
    "staff/customers.html",
    "staff/catalog.html",
    "staff/branches.html",
    "staff/schedule.html",
    "staff/reports.html",
    "features/page.html",
    "features/resource_list.html",
    "features/resource_detail.html",
    "features/resource_import.html",
    "features/reports.html",
    "features/search.html",
    "features/appointments.html",
    "features/cancel.html",
    "features/reschedule.html",
    "auth/password_reset.html",
    "auth/password_reset_done.html",
    "auth/password_reset_confirm.html",
    "auth/password_reset_complete.html",
    "auth/password_reset_email.txt",
    "auth/password_reset_subject.txt",
    "operations/notifications.html",
    "operations/points.html",
    "operations/audit.html",
    "operations/week.html",
    "operations/performance.html",
)


@register(Tags.templates)
def required_interface_templates(app_configs, **kwargs):
    from django.conf import settings
    from django.template import TemplateDoesNotExist, TemplateSyntaxError
    from django.template.loader import get_template

    errors = []
    for name in REQUIRED_TEMPLATES:
        try:
            get_template(name)
        except TemplateDoesNotExist:
            errors.append(
                Error(
                    f"Thiếu template: templates/{name}",
                    hint=f"Đặt file tại {settings.BASE_DIR / 'templates' / name}. "
                    "Chạy scripts/cap_nhat_du_an.py để đồng bộ đủ file.",
                    id="salon.E002",
                )
            )
        except TemplateSyntaxError as error:
            errors.append(Error(f"Template sai cú pháp: {name}: {error}", id="salon.E003"))
    return errors
