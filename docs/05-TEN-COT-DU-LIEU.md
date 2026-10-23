# Tên thuộc tính trong các bảng dữ liệu

Các cột của 12 bảng nghiệp vụ dùng tiếng Việt viết liền không dấu, chữ thường, không có dấu gạch dưới. Tên bảng giữ nguyên. Các kiểu dữ liệu vẫn bằng tiếng Anh và giữ nguyên kiểu, độ dài, tính NULL, khóa chính/ngoại và ràng buộc của bản trước.

Django ánh xạ tên thuộc tính Python sang tên cột PostgreSQL bằng `db_column`. Ví dụ `User.full_name` truy vấn cột `hoten`, `Appointment.branch_id` truy vấn cột `machinhanh`. Các bảng kỹ thuật do Django quản lý (quyền, nhóm, session, bảng nối phân quyền) dùng quy ước của framework.

Đã có database: chạy `python manage.py migrate --noinput` để áp dụng migration `0002_vietnamese_column_names`. Migration đổi tên cột, không xóa và tạo lại dữ liệu. Tệp `0001_initial.py` được giữ nguyên để có thể nâng cấp và hoàn tác đúng lịch sử.

Các giá trị enum như `booked`, `customer`, `cash` và các tham số API vẫn giữ nguyên; đây là giá trị dữ liệu/giao thức, không phải tên cột hoặc kiểu dữ liệu.

## 1. Bảng salon_branch

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `machinhanh` | `bigint` | PK; NOT NULL |
| `name` | `tenchinhanh` | `varchar(100)` | UNIQUE; NOT NULL |
| `address` | `diachi` | `varchar(250)` | NOT NULL |
| `phone` | `sodienthoai` | `varchar(10)` | NOT NULL |
| `opens_at` | `giomocua` | `time` | NOT NULL |
| `closes_at` | `giodongcua` | `time` | NOT NULL |
| `active` | `hoatdong` | `boolean` | NOT NULL |

## 2. Bảng salon_user

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `manguoidung` | `bigint` | PK; NOT NULL |
| `password` | `matkhau` | `varchar(128)` | NOT NULL |
| `last_login` | `landangnhapcuoi` | `timestamptz` | NULL |
| `is_superuser` | `laquantri` | `boolean` | NOT NULL |
| `username` | `tendangnhap` | `varchar(150)` | UNIQUE; NOT NULL |
| `first_name` | `ten` | `varchar(150)` | NOT NULL |
| `last_name` | `ho` | `varchar(150)` | NOT NULL |
| `email` | `thudientu` | `varchar(254)` | NOT NULL |
| `is_staff` | `lanhanvien` | `boolean` | NOT NULL |
| `is_active` | `hoatdong` | `boolean` | NOT NULL |
| `date_joined` | `ngaythamgia` | `timestamptz` | NOT NULL |
| `full_name` | `hoten` | `varchar(100)` | NOT NULL |
| `phone` | `sodienthoai` | `varchar(10)` | NOT NULL |
| `role` | `vaitro` | `varchar(20)` | NOT NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NULL |
| `points` | `diemtichluy` | `integer` | NOT NULL |

## 3. Bảng salon_service

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `madichvu` | `bigint` | PK; NOT NULL |
| `name` | `tendichvu` | `varchar(100)` | UNIQUE; NOT NULL |
| `description` | `mota` | `text` | NOT NULL |
| `kind` | `loaidichvu` | `varchar(10)` | NOT NULL |
| `price` | `giatien` | `integer` | NOT NULL |
| `duration` | `thoiluong` | `integer` | NOT NULL |
| `active` | `hoatdong` | `boolean` | NOT NULL |

## 4. Bảng salon_employee

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `manhanvien` | `bigint` | PK; NOT NULL |
| `name` | `hoten` | `varchar(100)` | NOT NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NOT NULL |
| `specialty` | `chuyenmon` | `varchar(150)` | NOT NULL |
| `bio` | `gioithieu` | `varchar(250)` | NOT NULL |
| `active` | `hoatdong` | `boolean` | NOT NULL |

## 5. Bảng salon_chair

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `maghe` | `bigint` | PK; NOT NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NOT NULL |
| `name` | `tenghe` | `varchar(30)` | NOT NULL |
| `active` | `hoatdong` | `boolean` | NOT NULL |

## 6. Bảng salon_shift

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `macalam` | `bigint` | PK; NOT NULL |
| `employee_id` | `manhanvien` | `bigint` | FK → salon_employee.manhanvien; NOT NULL |
| `start_at` | `thoigianbatdau` | `timestamptz` | NOT NULL |
| `end_at` | `thoigianketthuc` | `timestamptz` | NOT NULL |

## 7. Bảng salon_appointment

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `malichhen` | `bigint` | PK; NOT NULL |
| `customer_id` | `makhachhang` | `bigint` | FK → salon_user.manguoidung; NOT NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NOT NULL |
| `employee_id` | `manhanvien` | `bigint` | FK → salon_employee.manhanvien; NOT NULL |
| `chair_id` | `maghe` | `bigint` | FK → salon_chair.maghe; NULL |
| `start_at` | `thoigianbatdau` | `timestamptz` | NOT NULL |
| `end_at` | `thoigianketthuc` | `timestamptz` | NOT NULL |
| `status` | `trangthai` | `varchar(20)` | NOT NULL |
| `note` | `ghichu` | `varchar(500)` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 8. Bảng salon_appointmentitem

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `machitiet` | `bigint` | PK; NOT NULL |
| `appointment_id` | `malichhen` | `bigint` | FK → salon_appointment.malichhen; NOT NULL |
| `service_id` | `madichvu` | `bigint` | FK → salon_service.madichvu; NOT NULL |
| `name` | `tendichvu` | `varchar(100)` | NOT NULL |
| `price` | `giatien` | `integer` | NOT NULL |
| `duration` | `thoiluong` | `integer` | NOT NULL |

## 9. Bảng salon_invoice

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mahoadon` | `bigint` | PK; NOT NULL |
| `appointment_id` | `malichhen` | `bigint` | FK → salon_appointment.malichhen; UNIQUE; NOT NULL |
| `total` | `tongthanhtoan` | `integer` | NOT NULL |
| `method` | `phuongthucthanhtoan` | `varchar(10)` | NOT NULL |
| `paid_at` | `thoigianthanhtoan` | `timestamptz` | NOT NULL |
| `cashier_id` | `mathungan` | `bigint` | FK → salon_user.manguoidung; NOT NULL |

## 10. Bảng salon_review

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `madanhgia` | `bigint` | PK; NOT NULL |
| `appointment_id` | `malichhen` | `bigint` | FK → salon_appointment.malichhen; UNIQUE; NOT NULL |
| `rating` | `sosao` | `smallint` | NOT NULL |
| `comment` | `binhluan` | `varchar(500)` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 11. Bảng salon_notification

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mathongbao` | `bigint` | PK; NOT NULL |
| `recipient_id` | `manguoinhan` | `bigint` | FK → salon_user.manguoidung; NOT NULL |
| `message` | `noidung` | `varchar(250)` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 12. Bảng salon_auditlog

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `manhatky` | `bigint` | PK; NOT NULL |
| `actor_id` | `manguoithaotac` | `bigint` | FK → salon_user.manguoidung; NULL |
| `appointment_id` | `malichhen` | `bigint` | FK → salon_appointment.malichhen; NULL |
| `action` | `hanhdong` | `varchar(100)` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## Kiểm tra nhanh trong PostgreSQL

```sql
SELECT hoten, sodienthoai, vaitro FROM salon_user;
SELECT malichhen, makhachhang, thoigianbatdau, thoigianketthuc, trangthai FROM salon_appointment;
SELECT mahoadon, tongthanhtoan, phuongthucthanhtoan, thoigianthanhtoan FROM salon_invoice;
```

Các ràng buộc khoảng thời gian, check constraint và unique theo nhiều cột vẫn được mô tả trong `02-THIET-KE.md` và định nghĩa trong `salon/models.py`.
