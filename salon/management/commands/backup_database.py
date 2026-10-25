from datetime import datetime
from pathlib import Path
import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from salon.database_backup import backup


class Command(BaseCommand):
    help = 'Sao lưu PostgreSQL native dạng custom, kèm SHA256 và số dòng cùng snapshot.'
    def add_arguments(self, parser):
        parser.add_argument('--output', type=Path)
    def handle(self, *args, **options):
        output = options['output'] or settings.BASE_DIR/'.local/backups'/('gentleman-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.dump')
        try: path, tables = backup(output)
        except (psycopg.Error, OSError) as error:
            raise CommandError('Không sao lưu được. Kiểm tra PostgreSQL, quyền và đường dẫn file.') from error
        self.stdout.write(self.style.SUCCESS(f'Đã sao lưu: {path} · {len(tables)} bảng. Giữ cả file .dump.json đi kèm.'))
