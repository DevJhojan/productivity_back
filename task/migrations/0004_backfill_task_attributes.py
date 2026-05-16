from decimal import Decimal

from django.db import migrations


def forwards_func(apps, schema_editor):
    Task = apps.get_model("task", "Task")
    UserAttribute = apps.get_model("users", "UserAttribute")

    for task in Task.objects.filter(attribute__isnull=True).iterator():
        attribute, _ = UserAttribute.objects.get_or_create(
            user_id=task.owner_id,
            name="Strength",
            defaults={"points": Decimal("0.00")},
        )
        task.attribute_id = attribute.id
        task.save(update_fields=["attribute"])


def backwards_func(apps, schema_editor):
    Task = apps.get_model("task", "Task")
    Task.objects.all().update(attribute_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_backfill_user_attributes"),
        ("task", "0003_task_attribute"),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
