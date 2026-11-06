"""Read-only row-count audit; a count is never proof of authentic source data."""

from datetime import datetime, timezone
import json
from pathlib import Path
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

PUBLIC_CANDIDATES = {"Branch", "Service", "Product"}
SYSTEM_RECORDS = {"AuditLog", "Notification", "EmailOutbox", "AuthRateBucket", "AppointmentChange"}


class Command(BaseCommand):
    help = (
        "Đếm từng bảng và số còn thiếu so với mục tiêu; không tạo dữ liệu hoặc xác nhận nguồn giả."
    )

    def add_arguments(self, parser):
        parser.add_argument("--target", type=int, default=100)
        parser.add_argument("--output", type=Path)

    def handle(self, *args, **options):
        target = options["target"]
        if not 1 <= target <= 1000:
            raise CommandError("Mục tiêu phải trong khoảng 1–1000.")
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target_per_table": target,
            "database_written": False,
            "tables": [],
            "notice": "Số dòng không chứng minh dữ liệu là thật. verified_real_rows=null nghĩa là chưa kiểm chứng nguồn; không được đệm bản ghi giả cho đủ số.",
        }
        for model in apps.get_app_config("salon").get_models():
            name = model.__name__
            count = model.objects.count()
            public = name in PUBLIC_CANDIDATES
            if public:
                requirement = "Có thể đối chiếu danh mục công khai; cần đầy đủ trường bắt buộc và quyền vận hành trước khi nhập vào bảng nghiệp vụ."
            elif name in SYSTEM_RECORDS:
                requirement = "Bản ghi do thao tác/sự kiện thực tế phát sinh; không tạo 100 log hoặc thông báo giả."
            else:
                requirement = "Cần dữ liệu thực tế do đơn vị quản lý cung cấp hoặc giao dịch thật; không suy ra từ website công khai."
            report["tables"].append(
                {
                    "model": name,
                    "table": model._meta.db_table,
                    "row_count": count,
                    "shortfall_to_count_target": max(0, target - count),
                    "verified_real_rows": None,
                    "public_source_candidate": public,
                    "input_requirement": requirement,
                }
            )
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        output = options["output"]
        if output:
            try:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(text, encoding="utf-8")
            except OSError as error:
                raise CommandError("Không lưu được báo cáo kiểm đếm.") from error
        self.stdout.write(text, ending="")
