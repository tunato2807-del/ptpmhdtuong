from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from .forms import ProfileForm
from .models import User, AuditLog


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    profile_form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                profile_form = ProfileForm(request.POST, instance=user)
                if profile_form.is_valid():
                    # Do not overwrite points/roles/passwords changed by another request.
                    user = profile_form.save(commit=False)
                    user.save(update_fields=["full_name", "phone", "email"])
                    AuditLog.objects.create(actor=user, action="Cập nhật hồ sơ cá nhân")
                    messages.success(request, "Đã cập nhật thông tin cá nhân.")
                    return redirect("profile")
        elif action == "password":
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                password_form = PasswordChangeForm(user, request.POST)
                if password_form.is_valid():
                    user = password_form.save()
                    update_session_auth_hash(request, user)
                    AuditLog.objects.create(actor=user, action="Đổi mật khẩu cá nhân")
                    messages.success(
                        request, "Đã đổi mật khẩu. Bạn vẫn đang đăng nhập trên thiết bị này."
                    )
                    return redirect("profile")
        else:
            return HttpResponseBadRequest("Thao tác không hợp lệ.")
    return render(
        request,
        "public/profile.html",
        {"profile_form": profile_form, "password_form": password_form},
    )
