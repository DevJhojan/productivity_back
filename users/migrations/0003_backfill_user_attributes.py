from decimal import Decimal

from django.db import migrations


ATTRIBUTE_NAMES = [
    "Strength",
    "Vitality",
    "Agility",
    "Intelligence",
    "Perception",
]


def forwards_func(apps, schema_editor):
    User = apps.get_model("users", "User")
    UserAttribute = apps.get_model("users", "UserAttribute")

    for user in User.objects.all().iterator():
        base_points = Decimal(str(user.points or 0))
        for attribute_name in ATTRIBUTE_NAMES:
            UserAttribute.objects.get_or_create(
                user_id=user.id,
                name=attribute_name,
                defaults={"points": base_points},
            )


def backwards_func(apps, schema_editor):
    UserAttribute = apps.get_model("users", "UserAttribute")
    UserAttribute.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_userattribute"),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
