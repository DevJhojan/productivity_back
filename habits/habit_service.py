import json
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse

from funcs.system_levels import LevelSystem
from users.models_users import User, UserAttribute, ensure_default_attributes_for_user
from .models_habit import Habit, HabitLog
from .habit_serializer import habit_to_dict, _get_streak


def _load_json(request):
    try:
        return json.loads(request.body or "{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON body"}, status=400)


def _get_habit_or_404(habit_id):
    try:
        habit = Habit.objects.get(id=habit_id)
        return habit, None
    except Habit.DoesNotExist:
        return None, JsonResponse({"error": "Habit not found"}, status=404)


def _get_default_attribute_for_owner(owner_id: int) -> UserAttribute:
    owner = User.objects.get(id=owner_id)
    ensure_default_attributes_for_user(owner)
    attribute, _ = UserAttribute.objects.get_or_create(
        user_id=owner_id,
        name=UserAttribute.AttributeName.STRENGTH,
        defaults={"points": Decimal("0.00")},
    )
    return attribute


def _resolve_attribute_for_owner(owner_id: int, attribute_id: int | None):
    if not User.objects.filter(id=owner_id).exists():
        return None, JsonResponse({"error": "Owner not found"}, status=404)

    if attribute_id is None:
        return _get_default_attribute_for_owner(owner_id), None

    try:
        attribute = UserAttribute.objects.get(id=attribute_id)
    except UserAttribute.DoesNotExist:
        return None, JsonResponse({"error": "Attribute not found"}, status=404)

    if attribute.user_id != owner_id:
        return (
            None,
            JsonResponse(
                {"error": "Habit attribute must belong to habit owner"}, status=400
            ),
        )
    return attribute, None


# ── CRUD ──────────────────────────────────────────────────────────────────────


def list_habits(request):
    owner_id = request.GET.get("owner_id")
    qs = Habit.objects.select_related("attribute")
    if owner_id:
        qs = qs.filter(owner_id=owner_id)
    return JsonResponse([habit_to_dict(h) for h in qs], safe=False)


def create_habit(request):
    data, error = _load_json(request)
    if error:
        return error

    owner_id = data.get("owner_id")
    if not owner_id:
        return JsonResponse({"error": "owner_id is required"}, status=400)

    title = data.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "title is required"}, status=400)

    attribute, error = _resolve_attribute_for_owner(owner_id, data.get("attribute_id"))
    if error:
        return error

    habit = Habit.objects.create(
        owner_id=owner_id,
        attribute=attribute,
        title=title,
        description=data.get("description", ""),
        is_active=data.get("is_active", True),
    )
    return JsonResponse(habit_to_dict(habit), status=201)


def get_habit(request, habit_id):
    habit, error = _get_habit_or_404(habit_id)
    if error:
        return error
    return JsonResponse(habit_to_dict(habit))


def patch_habit(request, habit_id):
    habit, error = _get_habit_or_404(habit_id)
    if error:
        return error

    data, error = _load_json(request)
    if error:
        return error

    patchable = ["title", "description", "is_active"]
    for field in patchable:
        if field in data:
            setattr(habit, field, data[field])

    if "attribute_id" in data:
        attribute, error = _resolve_attribute_for_owner(
            habit.owner_id, data["attribute_id"]
        )
        if error:
            return error
        habit.attribute = attribute

    habit.save()
    return JsonResponse(habit_to_dict(habit))


def delete_habit(request, habit_id):
    habit, error = _get_habit_or_404(habit_id)
    if error:
        return error
    habit.delete()
    return JsonResponse({"deleted": True}, status=200)


# ── CHECK / UNCHECK ────────────────────────────────────────────────────────────


def check_habit(request, habit_id):
    habit, error = _get_habit_or_404(habit_id)
    if error:
        return error

    today = date.today()
    if HabitLog.objects.filter(habit=habit, date=today).exists():
        return JsonResponse({"error": "Habit already checked today"}, status=400)

    streak_day = _get_streak(habit) + 1
    earned = LevelSystem.get_points_from_rules(main_type="habit", habit_day=streak_day)

    attribute = habit.attribute
    owner = habit.owner
    previous_points = float(owner.points)

    with transaction.atomic():
        HabitLog.objects.create(
            habit=habit, date=today, points_earned=Decimal(str(earned))
        )
        attribute.points = Decimal(attribute.points) + Decimal(str(earned))
        attribute.save(update_fields=["points"])
        new_points = float(owner.recalculate_points_from_attributes())

    level_result = LevelSystem.handle_level_change(
        current_points=new_points,
        previous_points=previous_points,
    )

    response = habit_to_dict(habit)
    response["earned_points"] = earned
    response["streak_day"] = streak_day
    response["owner_points"] = new_points
    response["level_result"] = level_result
    return JsonResponse(response)


def uncheck_habit(request, habit_id):
    habit, error = _get_habit_or_404(habit_id)
    if error:
        return error

    today = date.today()
    try:
        log = HabitLog.objects.get(habit=habit, date=today)
    except HabitLog.DoesNotExist:
        return JsonResponse({"error": "Habit not checked today"}, status=400)

    attribute = habit.attribute
    owner = habit.owner

    with transaction.atomic():
        new_attr_points = max(
            Decimal("0.00"), Decimal(attribute.points) - Decimal(log.points_earned)
        )
        attribute.points = new_attr_points
        attribute.save(update_fields=["points"])
        log.delete()
        owner.recalculate_points_from_attributes()

    return JsonResponse(habit_to_dict(habit))
