import csv
from datetime import date, timedelta
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, Sum, Avg, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from .forms import LoginForm, RegisterForm, BookingForm, ReviewForm
from .models import (User, Branch, Service, Employee, Appointment, Invoice, Chair,
                     Shift, Review, AuditLog)
from .services import book, transition, local_at, available_slots

def operator_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_operator:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped

def branches_for(user):
    qs = Branch.objects.all()
    return qs.filter(pk=user.branch_id) if user.role == User.Role.RECEPTIONIST else qs

def appointments_for(user):
    qs = Appointment.objects.select_related('customer', 'employee', 'branch', 'chair').prefetch_related('items')
    if user.role == User.Role.CUSTOMER:
        return qs.filter(customer=user)
    if user.role == User.Role.RECEPTIONIST:
        return qs.filter(branch_id=user.branch_id)
    return qs

def chosen_day(request, key='date'):
    try:
        return date.fromisoformat(request.GET.get(key, timezone.localdate().isoformat()))
    except ValueError:
        messages.warning(request, 'Ngày không hợp lệ, đang hiển thị hôm nay.')
        return timezone.localdate()

def staff_scope(request):
    branches = branches_for(request.user)
    selected = request.GET.get('branch', '')
    branch = branches.filter(pk=int(selected)).first() if selected.isdigit() else None
    return branches, branch

class SignInView(LoginView):
    authentication_form = LoginForm
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    def get_success_url(self):
        return self.get_redirect_url() or reverse('dashboard' if self.request.user.is_operator else 'my_appointments')

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Tài khoản đã sẵn sàng. Hãy chọn lịch hẹn đầu tiên!')
        return redirect('booking')
    return render(request, 'auth/register.html', {'form': form})

def home(request):
    return render(request, 'public/home.html', {
        'services': Service.objects.filter(active=True), 'branches': Branch.objects.filter(active=True),
        'stylists': Employee.objects.filter(active=True).select_related('branch')[:6],
        'review_stats': Review.objects.aggregate(average=Avg('rating'), count=Count('id')),
    })

@login_required
def booking(request):
    initial = {'date': timezone.localdate() + timedelta(days=1)}
    if request.GET.get('branch', '').isdigit(): initial['branch'] = request.GET['branch']
    if request.GET.get('service', '').isdigit(): initial['services'] = [request.GET['service']]
    if request.GET.get('employee', '').isdigit(): initial['employee'] = request.GET['employee']
    form = BookingForm(request.POST or None, initial=initial, user=request.user)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        try:
            a = book(customer=d.get('customer') or request.user, branch_id=d['branch'].pk, employee_id=d['employee'].pk,
                     service_ids=[s.pk for s in d['services']], start=local_at(d['date'], d['time']), note=d['note'], actor=request.user)
        except (ValidationError, IntegrityError) as e:
            form.add_error(None, e if isinstance(e, ValidationError) else 'Lịch vừa thay đổi. Vui lòng chọn lại khung giờ.')
        else:
            messages.success(request, f'Đặt lịch {a.code} thành công. Hẹn gặp bạn tại {a.branch.name}!')
            return redirect('appointment_detail', pk=a.pk)
    return render(request, 'public/booking.html', {'form': form,
        'service_list': Service.objects.filter(active=True),
        'employee_data': list(Employee.objects.filter(active=True, branch__active=True).values('id', 'name', 'branch_id', 'specialty')),
        'service_data': list(Service.objects.filter(active=True).values('id', 'name', 'price', 'duration'))})

@require_GET
def slots(request):
    try:
        branch = Branch.objects.get(pk=int(request.GET['branch']), active=True)
        employee = Employee.objects.get(pk=int(request.GET['employee']), branch=branch, active=True)
        day = date.fromisoformat(request.GET['date'])
        ids = {int(x) for x in request.GET.getlist('services')}
        services = list(Service.objects.filter(pk__in=ids, active=True))
        if not ids or len(services) != len(ids): raise ValueError
        total_duration = sum(s.duration for s in services)
        if not timezone.localdate() <= day <= timezone.localdate() + timedelta(days=30): raise ValueError
    except (KeyError, ValueError, Branch.DoesNotExist, Employee.DoesNotExist, OverflowError):
        return JsonResponse({'error': 'Chọn chi nhánh, dịch vụ, stylist và ngày hợp lệ.'}, status=400)
    return JsonResponse({'slots': available_slots(branch, employee, day, total_duration),
                         'duration': total_duration, 'total': sum(s.price for s in services)})

@login_required
def my_appointments(request):
    qs = Appointment.objects.filter(customer=request.user).select_related('branch', 'employee').prefetch_related('items')
    return render(request, 'public/my_appointments.html', {
        'upcoming': qs.filter(status__in=['booked','checked_in','in_service']).order_by('start_at'),
        'history': qs.exclude(status__in=['booked','checked_in','in_service']).order_by('-start_at')[:30],
        'notifications': request.user.notifications.order_by('-created_at')[:5],
    })

@login_required
def appointment_detail(request, pk):
    a = get_object_or_404(appointments_for(request.user), pk=pk)
    chairs = Chair.objects.filter(branch=a.branch, active=True)
    return render(request, 'public/appointment_detail.html', {'appointment': a, 'chairs': chairs, 'review_form': ReviewForm()})

@login_required
@require_POST
def appointment_action(request, pk):
    get_object_or_404(appointments_for(request.user), pk=pk)
    try:
        a = transition(pk=pk, actor=request.user, action=request.POST.get('action'),
                       chair_id=request.POST.get('chair') if request.POST.get('chair', '').isdigit() else None,
                       method=request.POST.get('method', 'cash'), confirmation=request.POST.get('confirmation', ''))
    except (ValidationError, IntegrityError) as e:
        messages.error(request, ' '.join(e.messages) if isinstance(e, ValidationError) else 'Dữ liệu vừa thay đổi. Vui lòng thử lại.')
    else:
        messages.success(request, f'{a.code}: {a.get_status_display()}.')
    return redirect('appointment_detail', pk=pk)

@login_required
@require_POST
def review(request, pk):
    a = get_object_or_404(Appointment, pk=pk, customer=request.user, status='completed')
    form = ReviewForm(request.POST)
    if form.is_valid():
        try:
            obj = form.save(commit=False)
            obj.appointment = a
            with transaction.atomic():
                obj.save()
        except IntegrityError:
            messages.error(request, 'Bạn đã đánh giá lịch hẹn này.')
        else:
            messages.success(request, 'Cảm ơn bạn đã chia sẻ trải nghiệm!')
    else:
        messages.error(request, 'Chọn số sao từ 1 đến 5 và bình luận tối đa 500 ký tự.')
    return redirect('appointment_detail', pk=pk)

@login_required
def invoice(request, pk):
    a = get_object_or_404(appointments_for(request.user), pk=pk)
    inv = get_object_or_404(Invoice, appointment=a)
    return render(request, 'public/invoice.html', {'appointment': a, 'invoice': inv})

@operator_required
def dashboard(request):
    branches, branch = staff_scope(request)
    day = chosen_day(request)
    all_qs = appointments_for(request.user)
    if branch: all_qs = all_qs.filter(branch=branch)
    qs = all_qs.filter(start_at__date=day)
    invoices = Invoice.objects.filter(appointment__in=all_qs)
    daily_revenue = invoices.filter(paid_at__date=day).aggregate(total=Sum('total'))['total'] or 0
    query, status = request.GET.get('q', '').strip()[:100], request.GET.get('status', '')
    visible = qs
    if query: visible = visible.filter(Q(customer__full_name__icontains=query) | Q(customer__phone__icontains=query))
    if status in Appointment.Status.values: visible = visible.filter(status=status)
    chart = []
    for i in range(6, -1, -1):
        d = day-timedelta(days=i)
        total = invoices.filter(paid_at__date=d).aggregate(total=Sum('total'))['total'] or 0
        chart.append({'day': d, 'total': total})
    maximum = max([x['total'] for x in chart]) or 1
    for x in chart: x['height'] = round(x['total'] / maximum * 100)
    staff = Employee.objects.filter(branch__in=branches, active=True)
    if branch: staff = staff.filter(branch=branch)
    staff = staff.annotate(booking_count=Count('appointment', filter=Q(appointment__start_at__date=day)))
    return render(request, 'staff/dashboard.html', {
        'branches': branches, 'selected_branch': branch, 'day': day, 'q': query, 'status': status,
        'statuses': Appointment.Status.choices, 'appointments': Paginator(visible, 12).get_page(request.GET.get('page')),
        'total_count': qs.count(), 'completed_count': qs.filter(status='completed').count(),
        'waiting_count': qs.filter(status__in=['booked','checked_in']).count(), 'revenue': daily_revenue,
        'chart': chart, 'staff': staff[:6], 'active_staff_count': staff.count(),
    })

@operator_required
def customers(request):
    qs = User.objects.filter(role='customer')
    if request.user.role == User.Role.RECEPTIONIST:
        qs = qs.filter(appointments__branch_id=request.user.branch_id).distinct()
    query = request.GET.get('q', '').strip()[:100]
    if query: qs = qs.filter(Q(full_name__icontains=query) | Q(phone__icontains=query))
    # Branch-scoped counts: reception cannot infer history at other branches.
    condition = Q(appointments__branch_id=request.user.branch_id) if request.user.role == User.Role.RECEPTIONIST else Q()
    qs = qs.annotate(visits=Count('appointments', filter=condition & Q(appointments__status='completed'))).order_by('full_name')
    return render(request, 'staff/customers.html', {'customers': Paginator(qs, 20).get_page(request.GET.get('page')), 'q': query})

@operator_required
def catalog(request):
    return render(request, 'staff/catalog.html', {'services': Service.objects.all()})

@operator_required
def branch_list(request):
    return render(request, 'staff/branches.html', {'branches': branches_for(request.user).annotate(stylist_count=Count('employees', filter=Q(employees__active=True), distinct=True), chair_count=Count('chairs', filter=Q(chairs__active=True), distinct=True))})

@operator_required
def schedule(request):
    branches, branch = staff_scope(request)
    day = chosen_day(request)
    staff = Employee.objects.filter(branch__in=branches, active=True).select_related('branch')
    if branch: staff = staff.filter(branch=branch)
    data = []
    for e in staff:
        data.append({'employee': e, 'shifts': e.shifts.filter(start_at__date=day),
                     'appointments': appointments_for(request.user).filter(employee=e, start_at__date=day).exclude(status__in=['cancelled','no_show'])})
    return render(request, 'staff/schedule.html', {'rows': data, 'branches': branches, 'selected_branch': branch, 'day': day})

@operator_required
def reports(request):
    branches, branch = staff_scope(request)
    end = chosen_day(request, 'end')
    try: start = date.fromisoformat(request.GET.get('start', (end-timedelta(days=29)).isoformat()))
    except ValueError: start = end-timedelta(days=29)
    if start > end or (end-start).days > 366:
        messages.error(request, 'Khoảng báo cáo tối đa 366 ngày; ngày bắt đầu phải trước ngày kết thúc.')
        start = end-timedelta(days=29)
    appts = appointments_for(request.user)
    if branch: appts = appts.filter(branch=branch)
    qs = Invoice.objects.filter(appointment__in=appts, paid_at__date__gte=start, paid_at__date__lte=end).select_related('appointment__customer','appointment__branch','appointment__employee','cashier').order_by('-paid_at')
    summary = qs.aggregate(revenue=Sum('total'), count=Count('id'), average=Avg('total'))
    summary['total'] = summary.pop('revenue')
    per_branch = qs.values('appointment__branch__name').annotate(total=Sum('total'), count=Count('id')).order_by('-total')
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="doanh-thu.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Mã hóa đơn','Chi nhánh','Khách hàng','Thời gian','Thanh toán (VNĐ)','Phương thức'])
        def safe(value):
            value = str(value)
            return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value
        for inv in qs:
            writer.writerow([inv.code, safe(inv.appointment.branch.name), safe(inv.appointment.customer.full_name), timezone.localtime(inv.paid_at).isoformat(), inv.total, inv.get_method_display()])
        return response
    return render(request, 'staff/reports.html', {'branches': branches, 'selected_branch': branch,
        'start': start, 'end': end, 'summary': summary, 'per_branch': per_branch,
        'invoices': Paginator(qs, 20).get_page(request.GET.get('page'))})

@require_GET
def health(request):
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok', 'database': 'postgresql'})
