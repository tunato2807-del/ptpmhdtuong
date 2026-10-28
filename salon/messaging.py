"""Transactional outbox. Sending is explicit via dispatch_emails; app writes never send SMTP."""
from datetime import timedelta
from django.utils import timezone
from .models import EmailOutbox


def schedule_emails(appointment, message):
    a = appointment
    EmailOutbox.objects.filter(appointment=a, sent_at__isnull=True).update(cancelled=True)
    address = a.customer.email.strip()
    if not address:
        return
    body = (f'{message}\nLịch {a.code} · {a.branch.name}\n'
            f'{timezone.localtime(a.start_at):%H:%M %d/%m/%Y}\n'
            f'Stylist: {a.employee.name}\nLiên hệ: {a.branch.phone}')
    import uuid
    EmailOutbox.objects.create(appointment=a, key='event:'+uuid.uuid4().hex,
        recipient=address, subject=f'Gentleman · {a.code} · {message}'[:200], body=body, due_at=timezone.now())
    if a.status != 'booked':
        return
    for hours in (24, 2):
        due = a.start_at-timedelta(hours=hours)
        if due < timezone.now():
            continue
        key = f'reminder:{a.pk}:{a.start_at.isoformat()}:{hours}'
        item, created = EmailOutbox.objects.get_or_create(key=key, defaults={
            'appointment':a, 'recipient':address, 'subject':f'Gentleman · Nhắc lịch {a.code} trước {hours} giờ',
            'body':body, 'due_at':due})
        if not created and item.sent_at is None:
            EmailOutbox.objects.filter(pk=item.pk).update(cancelled=False, recipient=address, body=body)
