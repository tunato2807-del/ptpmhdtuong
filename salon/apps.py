from django.apps import AppConfig


class SalonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "salon"
    verbose_name = "Quản lý chuỗi cắt tóc"

    def ready(self):
        from . import checks  # noqa: F401
