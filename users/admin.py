from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Campos que se muestran al CREAR el usuario
    add_fieldsets = (
        (
            "Account",
            {
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "document_type",
                    "document_number",
                    "phone",
                    "address",
                    "birth_date",
                ),
            },
        ),
    )

    # Campos que se muestran al EDITAR el usuario
    fieldsets = UserAdmin.fieldsets + (
        (
            "Personal info",
            {
                "fields": (
                    "document_type",
                    "document_number",
                    "phone",
                    "address",
                    "birth_date",
                    "points",
                ),
            },
        ),
    )

    list_display = ("username", "email", "document_number", "points", "is_staff")
    search_fields = ("username", "email", "document_number")
    ordering = ("username",)
