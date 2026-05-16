from datetime import date

from .models_habit import Habit, HabitLog


def _get_streak(habit: Habit) -> int:
    """Count consecutive days of logs ending yesterday (or today if already checked)."""
    logs = set(
        HabitLog.objects.filter(habit=habit).values_list("date", flat=True)
    )
    if not logs:
        return 0

    today = date.today()
    # Start from yesterday when computing streak before today's check
    current = today
    if today not in logs:
        from datetime import timedelta
        current = today - timedelta(days=1)

    streak = 0
    from datetime import timedelta
    while current in logs:
        streak += 1
        current -= timedelta(days=1)
    return streak


def habit_to_dict(habit: Habit) -> dict:
    attribute = habit.attribute
    today = date.today()
    checked_today = HabitLog.objects.filter(habit=habit, date=today).exists()
    return {
        "id": habit.id,
        "owner_id": habit.owner_id,
        "attribute": {
            "id": attribute.id,
            "name": attribute.name,
            "points": str(attribute.points),
        },
        "title": habit.title,
        "description": habit.description,
        "is_active": habit.is_active,
        "streak": _get_streak(habit),
        "checked_today": checked_today,
        "created_at": habit.created_at.isoformat(),
        "updated_at": habit.updated_at.isoformat(),
    }
