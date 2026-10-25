from django.core.management.base import BaseCommand, CommandError
from django.db import connection, OperationalError


class Command(BaseCommand):
    help = 'Kiểm tra kết nối PostgreSQL; không hiển thị mật khẩu và không sửa dữ liệu.'

    def handle(self, *args, **options):
        config = connection.settings_dict
        self.stdout.write(f"Database: {config['NAME']} · User: {config['USER']} · Host: {config['HOST']} · Port: {config['PORT']}")
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except OperationalError:
            raise CommandError('Không kết nối được PostgreSQL. Kiểm tra dịch vụ đang chạy, database đã tạo, và POSTGRES_USER/POSTGRES_PASSWORD/HOST/PORT trong .env. Sửa .env (cùng thư mục manage.py), không phải .env.example. Mật khẩu là của PostgreSQL, không phải tài khoản web.') from None
        self.stdout.write(self.style.SUCCESS('Kết nối PostgreSQL thành công.'))
