"""A walk-in profile becomes a login only after the customer controls its email."""
from django.contrib.auth.forms import PasswordResetForm
from django.urls import path
from .models import User
from .operations import ResetView


class WalkInActivationForm(PasswordResetForm):
    def get_users(self,email):
        return (user for user in User.objects.filter(email__iexact=email,is_active=True,role='customer')
                if not user.has_usable_password())


class ActivateWalkInView(ResetView):
    form_class=WalkInActivationForm
    template_name='business/activation.html'


urlpatterns=[path('kich-hoat-tai-khoan/',ActivateWalkInView.as_view(),name='activate_walkin')]
