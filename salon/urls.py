from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dang-nhap/', views.SignInView.as_view(), name='login'),
    path('dang-ky/', views.register, name='register'),
    path('dang-xuat/', LogoutView.as_view(), name='logout'),
    path('dat-lich/', views.booking, name='booking'),
    path('lich-cua-toi/', views.my_appointments, name='my_appointments'),
    path('lich-hen/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    path('lich-hen/<int:pk>/thao-tac/', views.appointment_action, name='appointment_action'),
    path('lich-hen/<int:pk>/danh-gia/', views.review, name='review'),
    path('lich-hen/<int:pk>/hoa-don/', views.invoice, name='invoice'),
    path('api/khung-gio/', views.slots, name='slots'),
    path('quan-ly/', views.dashboard, name='dashboard'),
    path('quan-ly/khach-hang/', views.customers, name='customers'),
    path('quan-ly/dich-vu/', views.catalog, name='catalog'),
    path('quan-ly/chi-nhanh/', views.branch_list, name='branches'),
    path('quan-ly/ca-lam/', views.schedule, name='schedule'),
    path('quan-ly/bao-cao/', views.reports, name='reports'),
    path('health/', views.health, name='health'),
]
