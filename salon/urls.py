from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views, management_views, profile_views

urlpatterns = [
    path("", views.home, name="home"),
    path("dang-nhap/", views.SignInView.as_view(), name="login"),
    path("dang-ky/", views.register, name="register"),
    path("dang-xuat/", LogoutView.as_view(), name="logout"),
    path("tai-khoan/", profile_views.profile, name="profile"),
    path("dat-lich/", views.booking, name="booking"),
    path("lich-cua-toi/", views.my_appointments, name="my_appointments"),
    path("lich-hen/<int:pk>/", views.appointment_detail, name="appointment_detail"),
    path("lich-hen/<int:pk>/thao-tac/", views.appointment_action, name="appointment_action"),
    path("lich-hen/<int:pk>/danh-gia/", views.review, name="review"),
    path("lich-hen/<int:pk>/hoa-don/", views.invoice, name="invoice"),
    path("api/khung-gio/", views.slots, name="slots"),
    path("quan-ly/", views.dashboard, name="dashboard"),
    path("quan-ly/khach-hang/", views.customers, name="customers"),
    path("quan-ly/dich-vu/", views.catalog, name="catalog"),
    path("quan-ly/chi-nhanh/", views.branch_list, name="branches"),
    path("quan-ly/ca-lam/", views.schedule, name="schedule"),
    path("quan-ly/bao-cao/", views.reports, name="reports"),
    path("quan-ly/thiet-lap/", management_views.settings_home, name="settings"),
    path(
        "quan-ly/thiet-lap/<slug:resource>/", management_views.resource_list, name="resource_list"
    ),
    path(
        "quan-ly/thiet-lap/<slug:resource>/them/",
        management_views.resource_edit,
        name="resource_create",
    ),
    path(
        "quan-ly/thiet-lap/<slug:resource>/<int:pk>/sua/",
        management_views.resource_edit,
        name="resource_edit",
    ),
    path(
        "quan-ly/thiet-lap/<slug:resource>/<int:pk>/xoa/",
        management_views.resource_delete,
        name="resource_delete",
    ),
    path("health/", views.health, name="health"),
]

from .features import urlpatterns as feature_urls

feature_names = {item.name for item in feature_urls}
urlpatterns = feature_urls + [item for item in urlpatterns if item.name not in feature_names]

from .operations import urlpatterns as operation_urls

urlpatterns += operation_urls

from .business_views import urlpatterns as business_urls

urlpatterns += business_urls
from .activation import urlpatterns as activation_urls

urlpatterns += activation_urls
