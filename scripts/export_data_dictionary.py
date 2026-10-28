"""Export SQL column names/types and their Django mapping from the current models."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.apps import apps
from django.db import connection

lines = [
    "# Tên thuộc tính trong các bảng dữ liệu",
    "",
    "Các cột của 26 bảng ứng dụng (25 nghiệp vụ và bộ đếm xác thực) dùng tiếng Việt viết liền không dấu, chữ thường, không có dấu gạch dưới. "
    "Tên bảng giữ nguyên. Các kiểu dữ liệu vẫn bằng tiếng Anh. Migration đổi tên cột giữ nguyên kiểu dữ liệu cũ; các trường và bảng bổ sung có kiểu/ràng buộc theo thiết kế hiện tại.",
    "",
    "Django ánh xạ tên thuộc tính Python sang tên cột PostgreSQL bằng `db_column`. "
    "Ví dụ `User.full_name` truy vấn cột `hoten`, `Appointment.branch_id` truy vấn cột `machinhanh`. "
    "Các bảng kỹ thuật do Django quản lý (quyền, nhóm, session, bảng nối phân quyền) dùng quy ước của framework.",
    "",
    "Đã có database: chạy `python manage.py migrate --noinput` để áp dụng migration "
    "`0002_vietnamese_column_names` và các migration 0003–0010 bổ sung vận hành, kho, đối soát, lịch sử, hoàn điểm và giới hạn xác thực. Migration đổi tên cột không xóa và tạo lại dữ liệu. "
    "Tệp `0001_initial.py` được giữ nguyên để có thể nâng cấp và hoàn tác đúng lịch sử.",
    "",
    "Các giá trị enum như `booked`, `customer`, `cash` và các tham số API vẫn giữ nguyên; "
    "đây là giá trị dữ liệu/giao thức, không phải tên cột hoặc kiểu dữ liệu.",
    "",
]
count = 0
for index, model in enumerate(apps.get_app_config("salon").get_models(), 1):
    lines += [
        f"## {index}. Bảng {model._meta.db_table}",
        "",
        "| Thuộc tính Python | Tên cột tiếng Việt | Kiểu dữ liệu | Ràng buộc chính |",
        "|---|---|---|---|",
    ]
    for field in model._meta.local_fields:
        data_type = (
            field.db_type(connection)
            .replace("timestamp with time zone", "timestamptz")
            .replace("time without time zone", "time")
        )
        constraints = ["PK"] if field.primary_key else []
        if field.is_relation:
            constraints.append(
                f"FK → {field.target_field.model._meta.db_table}.{field.target_field.column}"
            )
        if field.unique and not field.primary_key:
            constraints.append("UNIQUE")
        constraints.append("NULL" if field.null else "NOT NULL")
        lines.append(
            f"| `{field.attname}` | `{field.column}` | `{data_type}` | {'; '.join(constraints)} |"
        )
        count += 1
    lines.append("")
lines += [
    "## Kiểm tra nhanh trong PostgreSQL",
    "",
    "```sql",
    "SELECT hoten, sodienthoai, vaitro FROM salon_user;",
    "SELECT malichhen, makhachhang, thoigianbatdau, thoigianketthuc, trangthai FROM salon_appointment;",
    "SELECT mahoadon, tongthanhtoan, phuongthucthanhtoan, thoigianthanhtoan FROM salon_invoice;",
    "```",
    "",
    "Các ràng buộc khoảng thời gian, check constraint và unique theo nhiều cột vẫn được mô tả trong "
    "`02-THIET-KE.md` và định nghĩa trong `salon/models.py`.",
    "",
]
(ROOT / "docs/05-TEN-COT-DU-LIEU.md").write_text("\n".join(lines))
print(
    f"Exported {count} SQL columns from {len(list(apps.get_app_config('salon').get_models()))} business tables."
)
