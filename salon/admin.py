from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import (User, Branch, Service, Employee, Chair, Shift, Appointment,
                     AppointmentItem, Invoice, Review, AuditLog, Notification, ACTIVE_STATUSES)

admin.site.site_header = 'GENTLEMAN · Thiết lập hệ thống'
admin.site.site_title = 'GENTLEMAN'
admin.site.index_title = 'Quản trị danh mục & nhân sự'

@admin.register(User)
class SalonUserAdmin(UserAdmin):
    list_display = ['username', 'full_name', 'phone', 'role', 'branch', 'is_active']
    list_filter = ['role', 'branch', 'is_active']
    search_fields = ['username', 'full_name', 'phone']
    readonly_fields = ['points']
    fieldsets = UserAdmin.fieldsets + (('Hồ sơ salon', {'fields': ['full_name','phone','role','branch','points']}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Hồ sơ salon', {'fields': ['full_name','phone','role','branch']}),)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name','address','phone','opens_at','closes_at','active']
    search_fields = ['name','address']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name','kind','price','duration','active']
    list_filter = ['kind','active']
    search_fields = ['name']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['name','branch','specialty','active']
    list_filter = ['branch','active']
    def get_readonly_fields(self, request, obj=None):
        # Moving a stylist with historical appointments would corrupt branch ownership.
        return ['branch'] if obj else []

@admin.register(Chair)
class ChairAdmin(admin.ModelAdmin):
    list_display = ['name','branch','active']
    list_filter = ['branch','active']
    def get_readonly_fields(self, request, obj=None): return ['branch'] if obj else []

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = '__all__'
    def clean(self):
        data = super().clean()
        employee, start, end = data.get('employee'), data.get('start_at'), data.get('end_at')
        if employee and start and end:
            s, e = timezone.localtime(start), timezone.localtime(end)
            if s.date() != e.date() or s.time() < employee.branch.opens_at or e.time() > employee.branch.closes_at:
                raise ValidationError('Ca làm phải nằm trong giờ mở cửa của một ngày.')
            if self.instance.pk:
                original = Shift.objects.get(pk=self.instance.pk)
                bookings = Appointment.objects.filter(employee=original.employee, status__in=ACTIVE_STATUSES,
                    start_at__gte=original.start_at, end_at__lte=original.end_at)
                if bookings.exists() and (employee.pk != original.employee_id or bookings.exclude(start_at__gte=start, end_at__lte=end).exists()):
                    raise ValidationError('Không được thay đổi ca làm khiến lịch hẹn đã đặt không còn được phục vụ.')
        return data

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    form = ShiftForm
    list_display = ['employee','start_at','end_at']
    list_filter = ['employee__branch','start_at']
    date_hierarchy = 'start_at'
    def has_delete_permission(self, request, obj=None): return False
    @transaction.atomic
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST':
            branch_ids = set()
            value = request.POST.get('employee', '')
            if value.isdigit() and len(value) < 19:
                branch_ids.update(Employee.objects.filter(pk=int(value)).values_list('branch_id', flat=True))
            if object_id and object_id.isdigit() and len(object_id) < 19:
                branch_ids.update(Shift.objects.filter(pk=int(object_id)).values_list('employee__branch_id', flat=True))
            # Hold the same locks as book() before validating or changing shift coverage.
            list(Branch.objects.select_for_update().filter(pk__in=branch_ids).order_by('pk'))
        return super().changeform_view(request, object_id, form_url, extra_context)

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False

@admin.register(Appointment)
class AppointmentAdmin(ReadOnlyAdmin):
    list_display = ['id','customer','branch','employee','start_at','status']
    list_filter = ['branch','status','start_at']
    search_fields = ['customer__full_name','customer__phone']

@admin.register(Invoice)
class InvoiceAdmin(ReadOnlyAdmin):
    list_display = ['id','appointment','total','method','paid_at','cashier']
    list_filter = ['method','paid_at']

@admin.register(Review)
class ReviewAdmin(ReadOnlyAdmin):
    list_display = ['appointment','rating','comment','created_at']

@admin.register(AuditLog)
class AuditAdmin(ReadOnlyAdmin):
    list_display = ['actor','appointment','action','created_at']
    list_filter = ['created_at']

admin.site.register(Notification, ReadOnlyAdmin)
