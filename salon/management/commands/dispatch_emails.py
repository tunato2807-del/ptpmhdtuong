from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from salon.models import EmailOutbox, EmployeeAbsence, BranchClosure


class Command(BaseCommand):
    help = "Gửi thư xác nhận/nhắc lịch đến hạn từ outbox; chạy định kỳ mỗi phút."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        sent = failed = skipped = 0
        if opts["dry_run"]:
            count = EmailOutbox.objects.filter(
                sent_at__isnull=True, cancelled=False, due_at__lte=timezone.now(), attempts__lt=5
            ).count()
            self.stdout.write(f"Có {count} thư đến hạn. Chưa gửi thư.")
            return
        for _ in range(min(max(opts["limit"], 1), 1000)):
            with transaction.atomic():
                item = (
                    EmailOutbox.objects.select_for_update(skip_locked=True)
                    .filter(
                        sent_at__isnull=True,
                        cancelled=False,
                        due_at__lte=timezone.now(),
                        attempts__lt=5,
                    )
                    .order_by("due_at", "pk")
                    .first()
                )
                if item is None:
                    break
                a = item.appointment
                if not a.customer.email or a.customer.email.casefold() != item.recipient.casefold():
                    item.cancelled = True
                    item.save(update_fields=["cancelled"])
                    skipped += 1
                    continue
                if item.key.startswith("reminder:"):
                    stale = (
                        a.status != "booked"
                        or a.start_at <= timezone.now()
                        or a.start_at.isoformat() not in item.key
                        or EmployeeAbsence.objects.filter(
                            employee=a.employee,
                            active=True,
                            start_at__lt=a.end_at,
                            end_at__gt=a.start_at,
                        ).exists()
                        or BranchClosure.objects.filter(
                            branch=a.branch,
                            active=True,
                            start_at__lt=a.end_at,
                            end_at__gt=a.start_at,
                        ).exists()
                    )
                    if stale:
                        item.cancelled = True
                        item.save(update_fields=["cancelled"])
                        skipped += 1
                        continue
                item.attempts += 1
                try:
                    if (
                        send_mail(
                            item.subject,
                            item.body,
                            settings.DEFAULT_FROM_EMAIL,
                            [item.recipient],
                            fail_silently=False,
                        )
                        != 1
                    ):
                        raise RuntimeError("Nhà cung cấp không xác nhận gửi thư")
                    item.sent_at = timezone.now()
                    item.last_error = ""
                    sent += 1
                except Exception as error:
                    # Do not expose provider responses, which may contain credentials or addresses.
                    item.last_error = type(error).__name__
                    from datetime import timedelta

                    item.due_at = timezone.now() + timedelta(minutes=min(60, 2**item.attempts))
                    failed += 1
                item.save(update_fields=["attempts", "sent_at", "last_error", "due_at"])
        self.stdout.write(f"Đã gửi {sent}; gửi lỗi {failed}; bỏ thư cũ {skipped}.")
