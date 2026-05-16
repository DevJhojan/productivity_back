from django.conf import settings
from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", 
        IN_PROGRESS = "IN_PROGRESS", 
        COMPLETED = "COMPLETED" 

    class Priority(models.TextChoices):
        IMPORTANT_URGENT = "IMPORTANT_URGENT", "important and urgent"
        IMPORTANT_NOT_URGENT = "IMPORTANT_NOT_URGENT", "important and not urgent"
        NOT_IMPORTANT_URGENT = "NOT_IMPORTANT_URGENT", "not important and urgent"
        NOT_IMPORTANT_NOT_URGENT = "NOT_IMPORTANT_NOT_URGENT", "not important and not urgent"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    priority = models.CharField(
        max_length=24,
        choices=Priority.choices,
        default=Priority.NOT_IMPORTANT_NOT_URGENT,
    )
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
