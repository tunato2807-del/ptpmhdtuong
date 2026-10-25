from django.db import migrations


def opening_balances(apps, schema_editor):
    User = apps.get_model('salon', 'User')
    Entry = apps.get_model('salon', 'PointEntry')
    alias = schema_editor.connection.alias
    for user in User.objects.using(alias).filter(points__gt=0).iterator():
        Entry.objects.using(alias).get_or_create(customer_id=user.pk, kind='opening',
            defaults={'amount': user.points, 'balance': user.points})


class Migration(migrations.Migration):
    dependencies = [('salon', '0003_pointentry_invoice_discount_invoice_points_used_and_more')]
    operations = [migrations.RunPython(opening_balances, migrations.RunPython.noop)]
