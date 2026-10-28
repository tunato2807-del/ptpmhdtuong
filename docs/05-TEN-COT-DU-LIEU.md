# Tên thuộc tính trong các bảng dữ liệu

Các cột của 25 bảng nghiệp vụ dùng tiếng Việt viết liền không dấu, chữ thường, không có dấu gạch dưới. Tên bảng giữ nguyên. Các kiểu dữ liệu vẫn bằng tiếng Anh. Migration đổi tên cột giữ nguyên kiểu dữ liệu cũ; các trường và bảng bổ sung có kiểu/ràng buộc theo thiết kế hiện tại.

Django ánh xạ tên thuộc tính Python sang tên cột PostgreSQL bằng `db_column`. Ví dụ `User.full_name` truy vấn cột `hoten`, `Appointment.branch_id` truy vấn cột `machinhanh`. Các bảng kỹ thuật do Django quản lý (quyền, nhóm, session, bảng nối phân quyền) dùng quy ước của framework.

Đã có database: chạy `python manage.py migrate --noinput` để áp dụng migration `0002_vietnamese_column_names` và các migration 0003–0007 bổ sung vận hành, kho, đối soát và lịch sử. Migration đổi tên cột không xóa và tạo lại dữ liệu. Tệp `0001_initial.py` được giữ nguyên để có thể nâng cấp và hoàn tác đúng lịch sử.

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
| `booking_days` | `songaydatruoc` | `smallint` | NOT NULL |
| `cancel_hours` | `giohuytruoc` | `smallint` | NOT NULL |
| `late_minutes` | `phutdenmuon` | `smallint` | NOT NULL |

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
| `points_debt` | `diemcanthuhoi` | `integer` | NOT NULL |
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
| `account_id` | `mataikhoan` | `bigint` | FK → salon_user.manguoidung; UNIQUE; NULL |
| `commission_percent` | `phantramhoahong` | `smallint` | NOT NULL |
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
| `checked_in_at` | `giokhachden` | `timestamptz` | NULL |
| `service_started_at` | `giophucvu` | `timestamptz` | NULL |
| `service_finished_at` | `gioxongdichvu` | `timestamptz` | NULL |
| `source` | `nguondat` | `varchar(12)` | NOT NULL |
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
| `discount` | `tiengiam` | `integer` | NOT NULL |
| `points_earned` | `diemdatich` | `integer` | NOT NULL |
| `points_debt_paid` | `diemdathuhoi` | `integer` | NOT NULL |
| `voucher_discount` | `giamvoucher` | `integer` | NOT NULL |
| `voucher_code` | `mavoucher` | `varchar(40)` | NOT NULL |
| `points_used` | `diemdadung` | `integer` | NOT NULL |
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
| `appointment_id` | `malichhen` | `bigint` | FK → salon_appointment.malichhen; NULL |
| `read_at` | `ngaydoc` | `timestamptz` | NULL |
| `message` | `noidung` | `varchar(250)` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 12. Bảng salon_auditlog

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `manhatky` | `bigint` | PK; NOT NULL |
| `actor_id` | `manguoithaotac` | `bigint` | FK → salon_user.manguoidung; NULL |
| `appointment_id` | `malichhen` | `bigint` | FK → salon_appointment.malichhen; NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NULL |
| `action` | `hanhdong` | `varchar(100)` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 13. Bảng salon_pointentry

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mabiendong` | `bigint` | PK; NOT NULL |
| `customer_id` | `makhachhang` | `bigint` | FK → salon_user.manguoidung; NOT NULL |
| `invoice_id` | `mahoadon` | `bigint` | FK → salon_invoice.mahoadon; NULL |
| `kind` | `loai` | `varchar(20)` | NOT NULL |
| `amount` | `sodiem` | `integer` | NOT NULL |
| `balance` | `sodusaubiendong` | `integer` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 14. Bảng salon_employeeabsence

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `manghiphep` | `bigint` | PK; NOT NULL |
| `employee_id` | `manhanvien` | `bigint` | FK → salon_employee.manhanvien; NOT NULL |
| `start_at` | `batdau` | `timestamptz` | NOT NULL |
| `end_at` | `ketthuc` | `timestamptz` | NOT NULL |
| `reason` | `lydo` | `varchar(250)` | NOT NULL |
| `actor_id` | `manguoitao` | `bigint` | FK → salon_user.manguoidung; NOT NULL |
| `active` | `hieuluc` | `boolean` | NOT NULL |

## 15. Bảng salon_branchclosure

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `malichnghi` | `bigint` | PK; NOT NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NOT NULL |
| `start_at` | `batdau` | `timestamptz` | NOT NULL |
| `end_at` | `ketthuc` | `timestamptz` | NOT NULL |
| `reason` | `lydo` | `varchar(250)` | NOT NULL |
| `active` | `hieuluc` | `boolean` | NOT NULL |

## 16. Bảng salon_appointmentchange

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mabienchuyen` | `bigint` | PK; NOT NULL |
| `appointment_id` | `malichhen` | `bigint` | FK → salon_appointment.malichhen; NOT NULL |
| `actor_id` | `manguoithuchien` | `bigint` | FK → salon_user.manguoidung; NULL |
| `action` | `thaotac` | `varchar(40)` | NOT NULL |
| `reason` | `lydo` | `varchar(250)` | NOT NULL |
| `before` | `truockhisua` | `jsonb` | NOT NULL |
| `after` | `saukhisua` | `jsonb` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 17. Bảng salon_emailoutbox

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mathugui` | `bigint` | PK; NOT NULL |
| `appointment_id` | `malichhen` | `bigint` | FK → salon_appointment.malichhen; NOT NULL |
| `key` | `khoagui` | `varchar(180)` | UNIQUE; NOT NULL |
| `recipient` | `emailnhan` | `varchar(254)` | NOT NULL |
| `subject` | `tieude` | `varchar(200)` | NOT NULL |
| `body` | `noidung` | `text` | NOT NULL |
| `due_at` | `giogui` | `timestamptz` | NOT NULL |
| `sent_at` | `daguiluc` | `timestamptz` | NULL |
| `cancelled` | `dahuy` | `boolean` | NOT NULL |
| `attempts` | `solanthu` | `smallint` | NOT NULL |
| `last_error` | `loicuoi` | `varchar(200)` | NOT NULL |

## 18. Bảng salon_voucher

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mauudai` | `bigint` | PK; NOT NULL |
| `code` | `mavoucher` | `varchar(40)` | UNIQUE; NOT NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NULL |
| `amount` | `sotiengiam` | `integer` | NOT NULL |
| `min_total` | `toithieu` | `integer` | NOT NULL |
| `starts_at` | `batdau` | `timestamptz` | NOT NULL |
| `ends_at` | `ketthuc` | `timestamptz` | NOT NULL |
| `max_uses` | `luottoida` | `integer` | NOT NULL |
| `active` | `hoatdong` | `boolean` | NOT NULL |

## 19. Bảng salon_voucheruse

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `maluotdung` | `bigint` | PK; NOT NULL |
| `voucher_id` | `mauudai` | `bigint` | FK → salon_voucher.mauudai; NOT NULL |
| `invoice_id` | `mahoadon` | `bigint` | FK → salon_invoice.mahoadon; UNIQUE; NOT NULL |
| `customer_id` | `makhachhang` | `bigint` | FK → salon_user.manguoidung; NOT NULL |

## 20. Bảng salon_product

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `masanpham` | `bigint` | PK; NOT NULL |
| `sku` | `makho` | `varchar(40)` | UNIQUE; NOT NULL |
| `name` | `tensanpham` | `varchar(150)` | NOT NULL |
| `unit` | `donvi` | `varchar(30)` | NOT NULL |
| `reorder_level` | `nguongton` | `integer` | NOT NULL |
| `active` | `hoatdong` | `boolean` | NOT NULL |

## 21. Bảng salon_stock

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `matonkho` | `bigint` | PK; NOT NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NOT NULL |
| `product_id` | `masanpham` | `bigint` | FK → salon_product.masanpham; NOT NULL |
| `quantity` | `soluongton` | `integer` | NOT NULL |

## 22. Bảng salon_stockmovement

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mabiendongkho` | `bigint` | PK; NOT NULL |
| `stock_id` | `matonkho` | `bigint` | FK → salon_stock.matonkho; NOT NULL |
| `amount` | `soluong` | `integer` | NOT NULL |
| `balance` | `tonsau` | `integer` | NOT NULL |
| `kind` | `loai` | `varchar(12)` | NOT NULL |
| `reference` | `maphieu` | `varchar(40)` | NOT NULL |
| `reason` | `lydo` | `varchar(250)` | NOT NULL |
| `actor_id` | `manguoitao` | `bigint` | FK → salon_user.manguoidung; NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 23. Bảng salon_commission

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mahoahong` | `bigint` | PK; NOT NULL |
| `invoice_id` | `mahoadon` | `bigint` | FK → salon_invoice.mahoadon; UNIQUE; NOT NULL |
| `employee_id` | `manhanvien` | `bigint` | FK → salon_employee.manhanvien; NOT NULL |
| `percent` | `tyle` | `smallint` | NOT NULL |
| `amount` | `sotien` | `integer` | NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 24. Bảng salon_refund

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `mahoantien` | `bigint` | PK; NOT NULL |
| `invoice_id` | `mahoadon` | `bigint` | FK → salon_invoice.mahoadon; UNIQUE; NOT NULL |
| `amount` | `sotienhoan` | `integer` | NOT NULL |
| `points_debt_added` | `diemthieuthuhoi` | `integer` | NOT NULL |
| `reason` | `lydo` | `varchar(250)` | NOT NULL |
| `actor_id` | `manguoithuchien` | `bigint` | FK → salon_user.manguoidung; NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## 25. Bảng salon_dailyclosing

| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |
|---|---|---|---|
| `id` | `machotso` | `bigint` | PK; NOT NULL |
| `branch_id` | `machinhanh` | `bigint` | FK → salon_branch.machinhanh; NOT NULL |
| `day` | `ngay` | `date` | NOT NULL |
| `expected_cash` | `tienmathethong` | `integer` | NOT NULL |
| `counted_cash` | `tienmatthucte` | `integer` | NOT NULL |
| `invoices_count` | `sohoadon` | `integer` | NOT NULL |
| `reason` | `ghichu` | `varchar(250)` | NOT NULL |
| `actor_id` | `manguoichot` | `bigint` | FK → salon_user.manguoidung; NOT NULL |
| `created_at` | `ngaytao` | `timestamptz` | NOT NULL |

## Kiểm tra nhanh trong PostgreSQL

```sql
SELECT hoten, sodienthoai, vaitro FROM salon_user;
SELECT malichhen, makhachhang, thoigianbatdau, thoigianketthuc, trangthai FROM salon_appointment;
SELECT mahoadon, tongthanhtoan, phuongthucthanhtoan, thoigianthanhtoan FROM salon_invoice;
```

Các ràng buộc khoảng thời gian, check constraint và unique theo nhiều cột vẫn được mô tả trong `02-THIET-KE.md` và định nghĩa trong `salon/models.py`.
