"""Password recovery writes only credentials, after validating fresh state."""
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import INTERNAL_RESET_SESSION_TOKEN, PasswordResetConfirmView
from django.db import transaction
from .models import User


class PasswordOnlyForm(SetPasswordForm):
    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.user.save(update_fields=['password'])
        return self.user


class LockedPasswordResetConfirmView(PasswordResetConfirmView):
    form_class=PasswordOnlyForm

    @transaction.atomic
    def form_valid(self, form):
        current=User.objects.select_for_update().filter(pk=self.user.pk,is_active=True).first()
        token=self.request.session.get(INTERNAL_RESET_SESSION_TOKEN)
        if current is None or not self.token_generator.check_token(current,token):
            form.add_error(None,'Liên kết không còn hợp lệ. Vui lòng yêu cầu liên kết mới.')
            return self.form_invalid(form)
        self.user=form.user=current
        return super().form_valid(form)
