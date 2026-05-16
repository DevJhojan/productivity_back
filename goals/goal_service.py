import json
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from funcs.system_levels import LevelSystem
from users.models_users import User, UserAttribute, ensure_default_attributes_for_user
from .models_goal import Goal
from .goal_serializer import goal_to_dict


def _load_json(request):
    try:
        return json.loads(request.body or "{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON body"}, status=400)


def _get_goal_or_404(goal_id):
    try:
        return Goal.objects.get(id=goal_id), None
    except Goal.DoesNotExist:
        return None, JsonResponse({"error": "Goal not found"}, status=404)


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
                {"error": "Goal attribute must belong to goal owner"}, status=400
            ),
        )
    return attribute, None


def _clean_choices_data(data: dict) -> dict:
    cleaned = data.copy()
    if "status" in cleaned and isinstance(cleaned["status"], str):
        cleaned["status"] = cleaned["status"].upper()
    if "priority" in cleaned and isinstance(cleaned["priority"], str):
        cleaned["priority"] = cleaned["priority"].upper()
    # goal_subtype stays lowercase snake_case — only strip whitespace
    if "goal_subtype" in cleaned and isinstance(cleaned["goal_subtype"], str):
        cleaned["goal_subtype"] = cleaned["goal_subtype"].strip().lower()
    return cleaned


# ── CRUD ──────────────────────────────────────────────────────────────────────

def list_goals(request):
    owner_id = request.GET.get("owner_id")
    qs = Goal.objects.select_related("attribute")
    if owner_id:
        qs = qs.filter(owner_id=owner_id)
    return JsonResponse([goal_to_dict(g) for g in qs], safe=False)


def create_goal(request):
    data, error = _load_json(request)
    if error:
        return error
    data = _clean_choices_data(data)

    owner_id = data.get("owner_id")
    if not owner_id:
        return JsonResponse({"error": "owner_id is required"}, status=400)

    title = data.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "title is required"}, status=400)

    goal_subtype = data.get("goal_subtype", "").strip()
    valid_subtypes = [c.value for c in Goal.GoalSubtype]
    if not goal_subtype:
        return JsonResponse({"error": "goal_subtype is required"}, status=400)
    if goal_subtype not in valid_subtypes:
        return JsonResponse(
            {"error": f"Invalid goal_subtype. Valid values: {valid_subtypes}"},
            status=400,
        )

    attribute, error = _resolve_attribute_for_owner(owner_id, data.get("attribute_id"))
    if error:
        return error

    goal = Goal.objects.create(
        owner_id=owner_id,
        attribute=attribute,
        title=title,
        description=data.get("description", ""),
        priority=data.get("priority", Goal.Priority.NOT_IMPORTANT_NOT_URGENT),
        goal_subtype=goal_subtype,
        status=data.get("status", Goal.Status.PENDING),
        due_date=data.get("due_date"),
    )
    return JsonResponse(goal_to_dict(goal), status=201)


def get_goal(request, goal_id):
    goal, error = _get_goal_or_404(goal_id)
    if error:
        return error
    return JsonResponse(goal_to_dict(goal))


def patch_goal(request, goal_id):
    goal, error = _get_goal_or_404(goal_id)
    if error:
        return error

    data, error = _load_json(request)
    if error:
        return error

    return _save_goal_with_level_logic(goal, data, partial=True)


def delete_goal(request, goal_id):
    goal, error = _get_goal_or_404(goal_id)
    if error:
        return error
    goal.delete()
    return JsonResponse({"deleted": True}, status=200)


# ── Points logic ───────────────────────────────────────────────────────────────

def _award_points_to_owner(goal) -> dict:
    goal.completed_at = timezone.now()
    owner = goal.owner
    attribute = goal.attribute

    previous_owner_points = float(owner.points)
    earned_points = LevelSystem.get_points_from_rules(
        main_type="goal",
        goal_subtype=goal.goal_subtype,
    )
    attribute.points = Decimal(attribute.points) + Decimal(str(earned_points))
    attribute.save(update_fields=["points"])
    new_owner_points = float(owner.recalculate_points_from_attributes())

    return {
        "earned_points": earned_points,
        "total_points": new_owner_points,
        "level_result": LevelSystem.handle_level_change(
            current_points=new_owner_points,
            previous_points=previous_owner_points,
        ),
    }


def _apply_goal_fields(goal, data: dict, partial: bool):
    patchable = ["title", "description", "priority", "goal_subtype", "status", "due_date"]
    if partial:
        for field in patchable:
            if field in data:
                setattr(goal, field, data[field])
    else:
        for field in patchable:
            setattr(goal, field, data.get(field, getattr(goal, field)))


def _save_goal_with_level_logic(goal, data: dict, partial: bool):
    data = _clean_choices_data(data)

    # Validate goal_subtype if being changed
    if "goal_subtype" in data:
        valid_subtypes = [c.value for c in Goal.GoalSubtype]
        if data["goal_subtype"] not in valid_subtypes:
            return JsonResponse(
                {"error": f"Invalid goal_subtype. Valid values: {valid_subtypes}"},
                status=400,
            )

    # Resolve attribute change if requested
    if "attribute_id" in data:
        attribute, error = _resolve_attribute_for_owner(goal.owner_id, data["attribute_id"])
        if error:
            return error
        goal.attribute = attribute

    previous_status = goal.status
    _apply_goal_fields(goal, data, partial=partial)

    became_completed = (
        previous_status != Goal.Status.COMPLETED
        and goal.status == Goal.Status.COMPLETED
    )

    earned_points = 0.0
    level_result = None

    with transaction.atomic():
        if became_completed:
            calc = _award_points_to_owner(goal)
            earned_points = calc["earned_points"]
            level_result = calc["level_result"]
        goal.save()

    response = goal_to_dict(goal)
    if became_completed:
        response["earned_points"] = earned_points
        response["level_result"] = level_result
        response["owner_points"] = float(goal.owner.points)
    return JsonResponse(response)
