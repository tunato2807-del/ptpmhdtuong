"""Synchronous, persistent Observer implementation, inside the caller's transaction."""
from dataclasses import dataclass
from .models import AuditLog, Notification

@dataclass(frozen=True)
class AppointmentEvent:
    appointment: object
    actor: object
    message: str

class AuditObserver:
    def update(self, event):
        AuditLog.objects.create(actor=event.actor, appointment=event.appointment, branch=event.appointment.branch, action=event.message)

class NotificationObserver:
    def update(self, event):
        Notification.objects.create(recipient=event.appointment.customer, appointment=event.appointment,
            message=f'{event.appointment.code}: {event.message}')

class AppointmentPublisher:
    def __init__(self, observers):
        self.observers = tuple(observers)
    def publish(self, event):
        from .messaging import schedule_emails
        schedule_emails(event.appointment, event.message)
        for observer in self.observers:
            observer.update(event)

publisher = AppointmentPublisher([AuditObserver(), NotificationObserver()])
