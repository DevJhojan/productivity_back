from django.contrib.auth.models import AbstractUser  # type: ignore
from django.db import models  # type: ignore


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

    def __str__(self):
        return self.username
