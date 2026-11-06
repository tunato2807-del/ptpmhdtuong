"""Create the first chain manager from the owner's explicitly entered identity."""

from getpass import getpass
import sys
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from salon.models import User


class Command(BaseCommand):
    help = "Tạo quản trị chuỗi từ thông tin thật do bạn nhập; không tạo tài khoản mẫu."

    def add_arguments(self, parser):
        parser.add_argument("--username")
        parser.add_argument("--full-name", dest="full_name")
        parser.add_argument("--email")

    def handle(self, *args, **options):
        if not sys.stdin.isatty():
            raise CommandError("Chạy create_manager trong terminal tương tác để nhập mật khẩu.")
        username = (options["username"] or input("Tên đăng nhập: ")).strip()
        full_name = (options["full_name"] or input("Họ tên của bạn: ")).strip()
        email = options["email"]
        if email is None:
            email = input("Email (có thể để trống): ").strip()
        user = User(username=username, full_name=full_name, email=email, role=User.Role.MANAGER)
        try:
            user.full_clean(exclude=["password"], validate_unique=False)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        if User.objects.filter(username=username).exists():
            raise CommandError("Tên đăng nhập đã tồn tại; không thay đổi hồ sơ hoặc quyền cũ.")
        password = getpass("Mật khẩu: ")
        confirmation = getpass("Nhập lại mật khẩu: ")
        if password != confirmation:
            raise CommandError("Hai lần nhập mật khẩu không khớp; chưa tạo tài khoản.")
        try:
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        user.set_password(password)
        try:
            with transaction.atomic():
                user.save(force_insert=True)
        except IntegrityError as error:
            raise CommandError("Tên đăng nhập vừa được sử dụng; chưa tạo tài khoản mới.") from error
        self.stdout.write(
            self.style.SUCCESS("Đã tạo quản trị chuỗi. Đăng nhập bằng tài khoản vừa nhập.")
        )
