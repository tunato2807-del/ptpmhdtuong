from django.db import migrations
from django.db.models import F


def offset_existing_balances(apps, schema_editor):
    """Keep net entitlement and append a correction; never rewrite old ledgers."""
    User = apps.get_model("salon", "User")
    Entry = apps.get_model("salon", "PointEntry")
    alias = schema_editor.connection.alias
    for user in (
        User.objects.using(alias).select_for_update().filter(points__gt=0, points_debt__gt=0)
    ):
        if not Entry.objects.using(alias).filter(customer_id=user.pk).exists():
            Entry.objects.using(alias).create(
                customer_id=user.pk, kind="opening", amount=user.points, balance=user.points
            )
        amount = min(user.points, user.points_debt)
        User.objects.using(alias).filter(pk=user.pk).update(
            points=F("points") - amount, points_debt=F("points_debt") - amount
        )
        Entry.objects.using(alias).create(
            customer_id=user.pk, kind="debt_recovery", amount=-amount, balance=user.points - amount
        )


class Migration(migrations.Migration):
    dependencies = [("salon", "0008_refund_entitlement")]
    # Financial correction is forward-only: reversing schema cannot undo refunds.
    operations = [migrations.RunPython(offset_existing_balances, migrations.RunPython.noop)]
