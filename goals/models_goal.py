from django.conf import settings
from django.db import models


class Goal(models.Model):
    class Priority(models.TextChoices):
        IMPORTANT_URGENT = "IMPORTANT_URGENT", "important and urgent"
        IMPORTANT_NOT_URGENT = "IMPORTANT_NOT_URGENT", "important and not urgent"
        NOT_IMPORTANT_URGENT = "NOT_IMPORTANT_URGENT", "not important and urgent"
        NOT_IMPORTANT_NOT_URGENT = (
            "NOT_IMPORTANT_NOT_URGENT",
            "not important and not urgent",
        )

    class GoalSubtype(models.TextChoices):
        WEEKLY_GOAL = "weekly_goal", "Weekly Goal"
        MONTHLY_PROJECT = "monthly_project", "Monthly Project"
        ANNUAL_PROJECT = "annual_project", "Annual Project"
        FIVE_YEAR_PROJECT = "five_year_project", "Five Year Project"

    class Status(models.TextChoices):
        PENDING = "PENDING"
        IN_PROGRESS = "IN_PROGRESS"
        COMPLETED = "COMPLETED"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals"
    )
    attribute = models.ForeignKey(
        "users.UserAttribute", on_delete=models.PROTECT, related_name="goals"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=24,
        choices=Priority.choices,
        default=Priority.NOT_IMPORTANT_NOT_URGENT,
    )
    goal_subtype = models.CharField(max_length=20, choices=GoalSubtype.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
