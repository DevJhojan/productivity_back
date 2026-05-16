from django.contrib.auth.models import AbstractUser  # type: ignore
from django.db import models  # type: ignore
from django.db.models.signals import post_delete, post_save  # type: ignore
from django.dispatch import receiver  # type: ignore
from decimal import Decimal, ROUND_HALF_UP
from funcs.system_levels import LevelSystem  # type: ignore


ATTRIBUTE_NAMES = [
    "Strength",
    "Vitality",
    "Agility",
    "Intelligence",
    "Perception",
]


class DocumentType(models.TextChoices):
    CC = "CC", "Cédula de Ciudadanía"
    CE = "CE", "Cédula de Extranjería"
    TI = "TI", "Tarjeta de Identidad"
    PASSPORT = "PASSPORT", "Pasaporte"
    NIT = "NIT", "Número de Identificación Tributaria"
    RC = "RC", "Registro Civil"
    OTHER = "OTHER", "Otro"


class Person(models.Model):
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.CC,
    )
    document_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.document_type} {self.document_number}"


class User(AbstractUser, Person):
    email = models.EmailField(unique=True)
    points = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def recalculate_points_from_attributes(self) -> Decimal:
        attrs = list(self.attributes.all())
        if not attrs:
            avg = Decimal("0.00")
        else:
            total = sum((attr.points for attr in attrs), Decimal("0.00"))
            avg = (total / Decimal(len(attrs))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        if self.points != avg:
            self.points = avg
            self.save(update_fields=["points"])
        return avg

    def get_level_state(self) -> dict:
        return LevelSystem.build_level_state(float(self.points))

    def __str__(self):
        return self.username


class UserAttribute(models.Model):
    class AttributeName(models.TextChoices):
        STRENGTH = "Strength", "Strength"
        VITALITY = "Vitality", "Vitality"
        AGILITY = "Agility", "Agility"
        INTELLIGENCE = "Intelligence", "Intelligence"
        PERCEPTION = "Perception", "Perception"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="attributes",
    )
    name = models.CharField(max_length=20, choices=AttributeName.choices)
    points = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_attribute_name_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.username}:{self.name}"


def ensure_default_attributes_for_user(user: User) -> None:
    base_points = Decimal(str(user.points or 0))
    for attribute_name in ATTRIBUTE_NAMES:
        UserAttribute.objects.get_or_create(
            user=user,
            name=attribute_name,
            defaults={"points": base_points},
        )


@receiver(post_save, sender=User)
def create_missing_user_attributes(sender, instance, created, **kwargs):
    if created:
        ensure_default_attributes_for_user(instance)


@receiver(post_save, sender=UserAttribute)
def sync_user_points_after_attribute_save(sender, instance, **kwargs):
    instance.user.recalculate_points_from_attributes()


@receiver(post_delete, sender=UserAttribute)
def sync_user_points_after_attribute_delete(sender, instance, **kwargs):
    instance.user.recalculate_points_from_attributes()
