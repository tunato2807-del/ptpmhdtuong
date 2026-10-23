"""Verify real PostgreSQL data/type preservation, including rollback and auth joins."""
from datetime import time, timedelta
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class VietnameseColumnMigrationTests(TransactionTestCase):
    old_target = [('salon', '0001_initial')]
    new_target = [('salon', '0002_vietnamese_column_names')]

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate(target)
        return executor.loader.project_state(target).apps

    def setUp(self):
        super().setUp()
        self.old_apps = self.migrate(self.old_target)

    def tearDown(self):
        try:
            self.migrate(self.new_target)
        finally:
            super().tearDown()

    def populate(self):
        def model(name): return self.old_apps.get_model('salon', name)
        start = timezone.now().replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(days=1)
        branch = model('Branch').objects.create(name='Chi nhánh thử nghiệm', address='Hồ Chí Minh', phone='0901234567', opens_at=time(9), closes_at=time(21))
        user = model('User').objects.create(username='khachmigration', password='!', full_name='Nguyễn Ánh', phone='0901234567', email='anh@example.com', points=42)
        employee = model('Employee').objects.create(name='Trần Bảo', branch=branch, specialty='Tạo kiểu', bio='Nội dung có dấu')
        chair = model('Chair').objects.create(branch=branch, name='Ghế số 1')
        model('Shift').objects.create(employee=employee, start_at=start, end_at=start+timedelta(hours=8))
        service = model('Service').objects.create(name='Cắt tóc', description='Dữ liệu tiếng Việt', price=120000, duration=30)
        appointment = model('Appointment').objects.create(customer=user, branch=branch, employee=employee, chair=chair, start_at=start, end_at=start+timedelta(minutes=30), status='completed', note='Giữ nguyên dữ liệu')
        model('AppointmentItem').objects.create(appointment=appointment, service=service, name=service.name, price=service.price, duration=service.duration)
        model('Invoice').objects.create(appointment=appointment, total=120000, method='cash', cashier=user)
        model('Review').objects.create(appointment=appointment, rating=5, comment='Hài lòng')
        model('Notification').objects.create(recipient=user, message='Lịch đã hoàn thành')
        model('AuditLog').objects.create(actor=user, appointment=appointment, action='Đã thanh toán')
        return user.pk, appointment.pk

    def snapshot(self, registry):
        data, types = {}, {}
        for model in registry.get_app_config('salon').get_models():
            data[model._meta.model_name] = list(model.objects.order_by('pk').values())
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT attname, format_type(atttypid, atttypmod) FROM pg_attribute '
                    'WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped',
                    [model._meta.db_table],
                )
                actual_types = dict(cursor.fetchall())
            types[model._meta.model_name] = {field.name: actual_types[field.column] for field in model._meta.local_fields}
        return data, types

    def test_existing_rows_and_postgresql_types_survive_column_renames(self):
        user_id, _ = self.populate()
        before = self.snapshot(self.old_apps)
        new_apps = self.migrate(self.new_target)
        self.assertEqual(self.snapshot(new_apps), before)
        for model in new_apps.get_app_config('salon').get_models():
            for field in model._meta.local_fields:
                with self.subTest(model=model.__name__, field=field.name):
                    self.assertRegex(field.column, r'^[a-z]+$')
        with connection.cursor() as cursor:
            cursor.execute('SELECT hoten, diemtichluy FROM salon_user WHERE manguoidung=%s', [user_id])
            self.assertEqual(cursor.fetchone(), ('Nguyễn Ánh', 42))

    def test_reverse_migration_preserves_rows_foreign_keys_and_auth_membership(self):
        user_id, appointment_id = self.populate()
        new_apps = self.migrate(self.new_target)
        User = new_apps.get_model('salon', 'User')
        Group = new_apps.get_model('auth', 'Group')
        user = User.objects.get(pk=user_id)
        group = Group.objects.create(name='Nhóm kiểm thử')
        user.groups.add(group)
        Appointment = new_apps.get_model('salon', 'Appointment')
        completed = Appointment.objects.get(pk=appointment_id)
        fields = dict(customer_id=user_id, branch_id=completed.branch_id, employee_id=completed.employee_id,
                      chair_id=completed.chair_id, start_at=completed.start_at, end_at=completed.end_at)
        Appointment.objects.create(**fields)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(**fields)
        before = self.snapshot(new_apps)
        restored_apps = self.migrate(self.old_target)
        self.assertEqual(self.snapshot(restored_apps), before)
        restored_user = restored_apps.get_model('salon', 'User').objects.get(pk=user_id)
        self.assertEqual(restored_user.groups.get().name, group.name)
        final_apps = self.migrate(self.new_target)
        self.assertEqual(self.snapshot(final_apps), before)
        self.assertEqual(final_apps.get_model('salon', 'User').objects.get(pk=user_id).groups.count(), 1)
