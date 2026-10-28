from django.core.management.base import BaseCommand
from django.utils import timezone
from salon.models import AuthRateBucket


class Command(BaseCommand):
    help='Chỉ dọn bộ đếm đăng nhập đã hết hạn; không xóa tài khoản hoặc nghiệp vụ.'
    def handle(self,*args,**options):
        count,_=AuthRateBucket.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f'Đã dọn {count} bộ đếm hết hạn.')
