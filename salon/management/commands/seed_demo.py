from datetime import timedelta, time
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from salon.models import (User, Branch, Service, Employee, Chair, Shift, Appointment,
                          AppointmentItem, Invoice, Review, Notification)
from salon.services import local_at

class Command(BaseCommand):
    help = 'Nạp dữ liệu trình diễn. Chạy lại không xóa dữ liệu, không đặt lại mật khẩu. Chỉ DEBUG=1.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise CommandError('Không nạp tài khoản demo khi DJANGO_DEBUG=0.')
        branches = []
        for name, address, phone in [
            ('GENTLEMAN Quận 1', '125 Nguyễn Thái Học, Quận 1, TP. Hồ Chí Minh', '0283822001'),
            ('GENTLEMAN Quận 3', '86 Võ Văn Tần, Quận 3, TP. Hồ Chí Minh', '0283822003'),
            ('GENTLEMAN Bình Thạnh', '212 Phan Văn Trị, Bình Thạnh, TP. Hồ Chí Minh', '0283822005'),
        ]:
            branch, _ = Branch.objects.get_or_create(name=name, defaults={'address':address,'phone':phone,'opens_at':time(9),'closes_at':time(21)})
            branches.append(branch)
            for i in range(1,5): Chair.objects.get_or_create(branch=branch, name=f'Ghế {i:02d}')
        services = []
        for name, kind, price, duration, description in [
            ('Cắt tóc thiết kế', 'hair', 100000, 30, 'Tư vấn kiểu tóc, cắt tạo kiểu và hoàn thiện bằng sản phẩm chuyên nghiệp.'),
            ('Combo Gentleman', 'combo', 180000, 60, 'Cắt thiết kế, gội thư giãn, chăm sóc da mặt và tạo kiểu. Một trải nghiệm trọn vẹn.'),
            ('Gội & massage thư giãn', 'care', 80000, 30, 'Làm sạch da đầu kết hợp massage nhẹ nhàng, tái tạo năng lượng cho ngày mới.'),
            ('Uốn tạo kiểu', 'hair', 350000, 90, 'Tạo độ phồng và nếp tóc tự nhiên, được tư vấn theo chất tóc và khuôn mặt.'),
            ('Chăm sóc râu', 'care', 70000, 30, 'Tỉa định hình, làm sạch và dưỡng râu. Gọn gàng, sắc nét đến từng chi tiết.'),
            ('Combo Signature', 'combo', 280000, 90, 'Cắt thiết kế, gội massage, chăm sóc râu và da mặt dành cho quý ông.'),
        ]:
            service, _ = Service.objects.get_or_create(name=name, defaults={'kind':kind,'price':price,'duration':duration,'description':description})
            services.append(service)
        employees = []
        for i, (name, specialty) in enumerate([
            ('Trần Minh Khang','Classic & modern fade'),('Lê Quốc Bảo','Layer & tạo kiểu'),
            ('Nguyễn Hoàng Nam','Texture & uốn'),('Phạm Anh Tú','Classic gentleman'),
            ('Võ Đức Huy','Skin fade & styling'),('Đặng Gia Minh','Layer & chăm sóc'),
        ]):
            employee, _ = Employee.objects.get_or_create(name=name, branch=branches[i//2], defaults={'specialty':specialty,'bio':'Chăm chút từng đường kéo, lắng nghe phong cách riêng của bạn.'})
            employees.append(employee)
        today = timezone.localdate()
        for employee in employees:
            for offset in range(-14,31):
                day = today+timedelta(days=offset)
                Shift.objects.get_or_create(employee=employee, start_at=local_at(day,time(9)), defaults={'end_at':local_at(day,time(21))})
        users = []
        for username, fullname, role, branch in [
            ('admin','Tô Hoàng Tuấn','manager',None),
            ('letan','Nguyễn Thảo Linh','receptionist',branches[0]),
            ('khachhang','Nguyễn Minh Anh','customer',None),
        ]:
            user, created = User.objects.get_or_create(username=username, defaults={'full_name':fullname,'role':role,'branch':branch,'phone':'0901234567','email':f'{username}@example.com','is_staff':role=='manager','is_superuser':role=='manager'})
            if created:
                user.set_password('Gentleman@2026'); user.save()
            users.append(user)
        customers = [users[2]]
        for i, name in enumerate(['Trần Quốc Huy','Lê Hoàng Phúc','Phạm Gia Bảo','Võ Minh Tuấn','Đỗ Anh Khoa','Bùi Đức Thịnh','Hoàng Nhật Nam','Trương Thanh Tùng','Vũ Hải Đăng','Lý Thành Đạt','Đinh Ngọc Sơn']):
            user, created = User.objects.get_or_create(username=f'demo-customer-{i+1}', defaults={'full_name':name,'phone':f'09123456{i:02d}','email':f'customer{i+1}@example.com'})
            if created: user.set_unusable_password(); user.save()
            customers.append(user)
        if not Appointment.objects.filter(note='Dữ liệu mẫu · seed_demo').exists():
            def add(day, hour, minute, employee, customer, service, status='booked', method='cash'):
                start = local_at(day,time(hour,minute))
                a = Appointment.objects.create(customer=customer, branch=employee.branch, employee=employee,
                    start_at=start, end_at=start+timedelta(minutes=service.duration),status=status,note='Dữ liệu mẫu · seed_demo')
                AppointmentItem.objects.create(appointment=a,service=service,name=service.name,price=service.price,duration=service.duration)
                if status in ['checked_in','in_service']:
                    a.chair = Chair.objects.filter(branch=employee.branch).first(); a.save()
                if status == 'completed':
                    inv = Invoice.objects.create(appointment=a,total=service.price,method=method,cashier=users[0])
                    Invoice.objects.filter(pk=inv.pk).update(paid_at=a.end_at)
                    customer.points += service.price//10000; customer.save(update_fields=['points'])
                return a
            for offset in range(14,0,-1):
                day = today-timedelta(days=offset)
                for index in range(6):
                    a = add(day,10+index,0,employees[index],customers[(index+offset)%12],services[(index+offset)%6],'completed', 'mock' if index%3==0 else 'cash')
                    if offset in [2,5] and index%2==0:
                        Review.objects.create(appointment=a,rating=5 if index != 4 else 4,comment='Không gian chỉn chu, stylist tư vấn rất tận tâm. (Đánh giá mẫu)')
            for index in range(12):
                status = ['completed','completed','booked','in_service','checked_in','booked','booked','booked','cancelled','booked','booked','booked'][index]
                add(today,9+index//2,0,employees[index%6],customers[index],services[index%3],status)
            for index in range(6):
                add(today+timedelta(days=1),10+index,0,employees[index],customers[index],services[index%3])
            Notification.objects.create(recipient=users[2],message='Chào mừng bạn đến GENTLEMAN. Đây là môi trường trình diễn có dữ liệu mẫu.')
        self.stdout.write(self.style.SUCCESS(f'Sẵn sàng: {Branch.objects.count()} chi nhánh, {Employee.objects.count()} stylist, {Service.objects.count()} dịch vụ, {Appointment.objects.count()} lịch hẹn.'))
        self.stdout.write('Tài khoản mẫu: admin / letan / khachhang. Mật khẩu được ghi trong README; tài khoản đã có được giữ nguyên.')
