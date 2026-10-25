from pathlib import Path
import psycopg
from django.core.management.base import BaseCommand, CommandError
from salon.database_backup import restore


class Command(BaseCommand):
    help = 'Phục hồi vào database MỚI và đối chiếu số dòng; không ghi đè database đang dùng.'
    def add_arguments(self, parser):
        parser.add_argument('--file', type=Path, required=True)
        parser.add_argument('--target-db', required=True)
        parser.add_argument('--confirm', required=True)
    def handle(self, *args, **options):
        try: tables = restore(options['file'], options['target_db'], options['confirm'])
        except (psycopg.Error, OSError) as error:
            raise CommandError('Không phục hồi được. Database gốc giữ nguyên; kiểm tra quyền CREATEDB và pg_restore.') from error
        self.stdout.write(self.style.SUCCESS(f'Đã phục hồi và kiểm tra {len(tables)} bảng trong {options["target_db"]}. Database gốc không thay đổi.'))
