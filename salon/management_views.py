"""First-party resource management. Authorization is enforced on every request."""
from dataclasses import dataclass
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import connection, transaction, IntegrityError
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .forms import BranchForm, ServiceForm, EmployeeForm, ChairForm, ShiftForm, AccountForm, ConfirmDeleteForm
from .models import Branch, Service, Employee, Chair, Shift, User, Appointment, AuditLog, ACTIVE_STATUSES


@dataclass(frozen=True)
class Resource:
    key: str
    title: str
    singular: str
    model: type
    form: type
    search: tuple
    columns: tuple
    description: str


RESOURCES = {
    r.key: r for r in [
        Resource('dich-vu', 'Dịch vụ & combo', 'dịch vụ', Service, ServiceForm, ('name', 'description'),
                 ('Dịch vụ', 'Nhóm', 'Giá', 'Thời lượng', 'Trạng thái'), 'Chỉnh sửa bảng giá, thời lượng và các gói chăm sóc.'),
        Resource('chi-nhanh', 'Chi nhánh', 'chi nhánh', Branch, BranchForm, ('name', 'address'),
                 ('Chi nhánh', 'Địa chỉ', 'Điện thoại', 'Giờ mở cửa', 'Trạng thái'), 'Quản lý điểm phục vụ và giờ hoạt động.'),
        Resource('stylist', 'Đội ngũ stylist', 'stylist', Employee, EmployeeForm, ('name', 'specialty', 'branch__name'),
                 ('Stylist', 'Chi nhánh', 'Chuyên môn', 'Trạng thái'), 'Cập nhật thông tin, chuyên môn và tình trạng làm việc.'),
        Resource('ghe', 'Ghế cắt', 'ghế cắt', Chair, ChairForm, ('name', 'branch__name'),
                 ('Ghế', 'Chi nhánh', 'Trạng thái'), 'Sắp xếp ghế tại từng chi nhánh.'),
        Resource('ca-lam', 'Ca làm việc', 'ca làm', Shift, ShiftForm, ('employee__name', 'employee__branch__name'),
                 ('Stylist', 'Chi nhánh', 'Bắt đầu', 'Kết thúc'), 'Tạo và điều chỉnh ca làm, kiểm tra lịch hẹn liên quan.'),
        Resource('tai-khoan', 'Tài khoản', 'tài khoản', User, AccountForm, ('username', 'full_name', 'phone', 'email'),
                 ('Họ tên', 'Tên đăng nhập', 'Vai trò', 'Chi nhánh', 'Trạng thái'), 'Tạo tài khoản, phân vai trò và quản lý quyền đăng nhập.'),
    ]
}


def manager_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_manager:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def get_resource(key):
    if key not in RESOURCES:
        raise Http404
    return RESOURCES[key]


def lock_management(actor):
    # Serialize administrative edits and last-manager checks. Take the same branch
    # locks as booking/checkout BEFORE locking users, in a stable order.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext('gentleman-resource-management'))")
    list(Branch.objects.select_for_update().order_by('pk').values_list('pk', flat=True))
    if not User.objects.filter(pk=actor.pk, role=User.Role.MANAGER, is_active=True).exists():
        raise PermissionDenied


def resource_queryset(resource):
    qs = resource.model.objects.all()
    if resource.model in (Employee, Chair, User):
        qs = qs.select_related('branch')
    elif resource.model is Shift:
        qs = qs.select_related('employee__branch')
    return qs.order_by('-pk')


def row_values(resource, obj):
    active = 'Đang hoạt động' if getattr(obj, 'active', True) else 'Tạm ngừng'
    if resource.model is Service:
        return [obj.name, obj.get_kind_display(), f'{obj.price:,} ₫'.replace(',', '.'), f'{obj.duration} phút', active]
    if resource.model is Branch:
        return [obj.name, obj.address, obj.phone, f'{obj.opens_at:%H:%M} – {obj.closes_at:%H:%M}', active]
    if resource.model is Employee:
        return [obj.name, obj.branch.name, obj.specialty, active]
    if resource.model is Chair:
        return [obj.name, obj.branch.name, 'Sẵn sàng' if obj.active else 'Tạm ngừng']
    if resource.model is Shift:
        return [obj.employee.name, obj.employee.branch.name,
                timezone.localtime(obj.start_at).strftime('%H:%M · %d/%m/%Y'),
                timezone.localtime(obj.end_at).strftime('%H:%M · %d/%m/%Y')]
    return [str(obj), obj.username, obj.get_role_display(), str(obj.branch or '—'), 'Được đăng nhập' if obj.is_active else 'Đã khóa']


@manager_required
@require_http_methods(['GET'])
def settings_home(request):
    resources = [{'resource': r, 'count': r.model.objects.count()} for r in RESOURCES.values()]
    return render(request, 'staff/settings.html', {'resources': resources, 'nav_section': 'settings'})


@manager_required
@require_http_methods(['GET'])
def resource_list(request, resource):
    spec = get_resource(resource)
    query = request.GET.get('q', '').strip()[:100]
    qs = resource_queryset(spec)
    if query:
        condition = Q()
        for field in spec.search:
            condition |= Q(**{f'{field}__icontains': query})
        qs = qs.filter(condition)
    page = Paginator(qs, 20).get_page(request.GET.get('page'))
    rows = [{'object': obj, 'values': row_values(spec, obj)} for obj in page]
    return render(request, 'staff/resource_list.html', {'resource': spec, 'rows': rows, 'page_obj': page,
                                                        'q': query, 'nav_section': 'settings'})


@manager_required
@require_http_methods(['GET', 'POST'])
def resource_edit(request, resource, pk=None):
    spec = get_resource(resource)
    instance = get_object_or_404(spec.model, pk=pk) if pk is not None else None
    extra = {'actor': request.user} if spec.model is User else {}
    if request.method == 'POST':
        try:
            with transaction.atomic():
                lock_management(request.user)
                if pk is not None:
                    instance = get_object_or_404(spec.model.objects.select_for_update(), pk=pk)
                form = spec.form(request.POST, instance=instance, **extra)
                if form.is_valid():
                    obj = form.save()
                    AuditLog.objects.create(actor=request.user, action=f'{"Sửa" if pk else "Tạo"} {spec.singular} #{obj.pk}'[:100])
                    messages.success(request, f'Đã lưu {spec.singular}.')
                    return redirect('resource_list', resource=resource)
        except IntegrityError:
            form.add_error(None, 'Dữ liệu bị trùng hoặc vừa thay đổi. Vui lòng kiểm tra lại thông tin và ca làm.')
    else:
        form = spec.form(instance=instance, **extra)
    return render(request, 'staff/resource_form.html', {'resource': spec, 'object': instance, 'form': form,
                                                        'nav_section': 'settings', 'editing': pk is not None})


def guard_delete(spec, obj, actor):
    if spec.model is User:
        if obj.pk == actor.pk:
            raise ValidationError('Bạn không thể xóa tài khoản đang đăng nhập.')
        if obj.role == User.Role.MANAGER and obj.is_active and User.objects.filter(role=User.Role.MANAGER, is_active=True).count() <= 1:
            raise ValidationError('Phải giữ ít nhất một quản trị viên đang hoạt động.')
    if spec.model is Shift and Appointment.objects.filter(employee=obj.employee, status__in=ACTIVE_STATUSES,
            start_at__gte=obj.start_at, end_at__lte=obj.end_at).exists():
        raise ValidationError('Ca làm đang phục vụ lịch hẹn đã đặt. Không thể xóa ca này.')


@manager_required
@require_http_methods(['GET', 'POST'])
def resource_delete(request, resource, pk):
    spec = get_resource(resource)
    obj = get_object_or_404(spec.model, pk=pk)
    form = ConfirmDeleteForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                lock_management(request.user)
                obj = get_object_or_404(spec.model.objects.select_for_update(), pk=pk)
                guard_delete(spec, obj, request.user)
                obj.delete()
                AuditLog.objects.create(actor=request.user, action=f'Xóa {spec.singular} #{pk}'[:100])
            messages.success(request, f'Đã xóa {spec.singular}.')
            return redirect('resource_list', resource=resource)
        except ProtectedError:
            form.add_error(None, 'Bản ghi đang được liên kết với lịch hẹn, hóa đơn hoặc nguồn lực khác nên không thể xóa. Bạn có thể chọn Sửa để tạm ngừng hoạt động, hoặc xử lý các liên kết chưa dùng trước.')
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, 'Dữ liệu vừa thay đổi. Vui lòng tải lại và kiểm tra các liên kết trước khi xóa.')
    return render(request, 'staff/resource_delete.html', {'resource': spec, 'object': obj, 'form': form,
                                                          'nav_section': 'settings'})
