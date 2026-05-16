# task_service.py
import json
from decimal import Decimal  # Asegura una inserción limpia en PostgreSQL
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from funcs.system_levels import LevelSystem
from users.models_users import User, UserAttribute, ensure_default_attributes_for_user
from .models_task import Task
from .task_serializer import task_to_dict


def _load_json(request):
    try:
        return json.loads(request.body or "{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON body"}, status=400)


def list_tasks():
    tasks = Task.objects.all()
    return JsonResponse([task_to_dict(task) for task in tasks], safe=False)


# --- NUEVA FUNCIÓN HELPER PARA NORMALIZAR TEXTCHOICES ---
def _clean_choices_data(data: dict) -> dict:
    """Convierte campos de opciones a mayúsculas para que coincidan con TextChoices."""
    cleaned = data.copy()
    if "status" in cleaned and isinstance(cleaned["status"], str):
        cleaned["status"] = cleaned["status"].upper()
    if "priority" in cleaned and isinstance(cleaned["priority"], str):
        cleaned["priority"] = cleaned["priority"].upper()
    return cleaned


def create_task(request):
    data, error = _load_json(request)
    if error:
        return error
    data = _clean_choices_data(data)  # Normalizamos aquí también

    owner_id = data.get("owner_id")
    if not owner_id:
        return JsonResponse({"error": "owner_id is required"}, status=400)
    if not User.objects.filter(id=owner_id).exists():
        return JsonResponse({"error": "Owner not found"}, status=404)

    attribute, error = _resolve_attribute_for_owner(
        owner_id=owner_id,
        attribute_id=data.get("attribute_id"),
    )
    if error:
        return error

    task = Task.objects.create(
        title=data.get("title", ""),
        description=data.get("description", ""),
        status=data.get("status", Task.Status.PENDING),
        priority=data.get("priority", Task.Priority.NOT_IMPORTANT_NOT_URGENT),
        owner_id=owner_id,
        attribute=attribute,
    )
    return JsonResponse(task_to_dict(task), status=201)


def get_task_or_404(task_id):
    try:
        return Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return None


def _get_points_params_for_task() -> tuple[str, str | None]:
    # Task model always represents a simple task.
    return ("task", None)


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
                {"error": "Task attribute must belong to task owner"},
                status=400,
            ),
        )
    return attribute, None


def _validate_and_attach_task_attribute(task: Task):
    attribute, error = _resolve_attribute_for_owner(
        owner_id=task.owner_id,
        attribute_id=task.attribute_id,
    )
    if error:
        return error
    task.attribute = attribute
    return None


def _apply_task_fields(task, data, partial: bool):
    fields = [
        "title",
        "description",
        "status",
        "priority",
        "due_date",
        "owner_id",
        "attribute_id",
    ]

    if partial:
        for field in fields:
            if field in data:
                setattr(task, field, data[field])
    else:
        task.title = data.get("title", task.title)
        task.description = data.get("description", task.description)
        task.status = data.get("status", task.status)
        task.priority = data.get("priority", task.priority)
        task.due_date = data.get("due_date", task.due_date)
        task.owner_id = data.get("owner_id", task.owner_id)


def _award_points_to_owner(task) -> dict:
    task.completed_at = timezone.now()
    owner = task.owner
    attribute = task.attribute
    main_type, goal_subtype = _get_points_params_for_task()

    previous_owner_points = float(owner.points)
    earned_points = LevelSystem.get_points_from_rules(main_type=main_type)
    attribute.points = Decimal(attribute.points) + Decimal(str(earned_points))
    attribute.save(update_fields=["points"])
    new_owner_points = float(owner.recalculate_points_from_attributes())

    return {
        "task_completed": True,
        "main_type": main_type,
        "goal_subtype": goal_subtype,
        "earned_points": earned_points,
        "total_points": new_owner_points,
        "level_result": LevelSystem.handle_level_change(
            current_points=new_owner_points,
            previous_points=previous_owner_points,
        ),
    }


def _build_response(task, became_completed, earned_points, level_result) -> dict:
    response = task_to_dict(task)
    if became_completed:
        response["earned_points"] = earned_points
        response["level_result"] = level_result
        response["owner_points"] = float(task.owner.points)
    return JsonResponse(response)


def _save_task_with_level_logic(task, data, partial: bool):
    # MANDATORIO: Limpiamos y normalizamos los strings de estado/prioridad antes de evaluar
    data = _clean_choices_data(data)

    previous_status = task.status
    _apply_task_fields(task, data, partial=partial)
    validation_error = _validate_and_attach_task_attribute(task)
    if validation_error:
        return validation_error

    # Ahora sí: "COMPLETED" == "COMPLETED" dará True de manera consistente
    became_completed = (
        previous_status != Task.Status.COMPLETED
        and task.status == Task.Status.COMPLETED
    )

    earned_points = 0.0
    level_result = None

    with transaction.atomic():
        if became_completed:
            calc = _award_points_to_owner(task)
            earned_points = calc["earned_points"]
            level_result = calc["level_result"]
        task.save()

    return _build_response(task, became_completed, earned_points, level_result)


def update_task(task, data):
    return _save_task_with_level_logic(task, data, partial=False)


def patch_task(task, data):
    return _save_task_with_level_logic(task, data, partial=True)


def change_task_status(request, task):
    data, error = _load_json(request)
    if error:
        return error

    new_status = str(data.get("status", "")).strip().upper()
    valid = [s.value for s in Task.Status]
    if new_status not in valid:
        return JsonResponse(
            {"error": f"Invalid status. Valid values: {valid}"}, status=400
        )

    previous_status = task.status
    if previous_status == new_status:
        return JsonResponse(task_to_dict(task))

    if task.attribute is None:
        task.attribute = _get_default_attribute_for_owner(task.owner_id)

    attribute = task.attribute
    owner = task.owner
    previous_owner_points = float(owner.points)
    earned_points = None

    going_to_completed = (
        previous_status != Task.Status.COMPLETED and new_status == Task.Status.COMPLETED
    )
    leaving_completed = (
        previous_status == Task.Status.COMPLETED and new_status != Task.Status.COMPLETED
    )

    with transaction.atomic():
        if going_to_completed:
            points = LevelSystem.get_points_from_rules(main_type="task")
            attribute.points = Decimal(attribute.points) + Decimal(str(points))
            attribute.save(update_fields=["points"])
            task.completed_at = timezone.now()
            earned_points = points
        elif leaving_completed:
            points = LevelSystem.get_points_from_rules(main_type="task")
            attribute.points = max(
                Decimal("0.00"), Decimal(attribute.points) - Decimal(str(points))
            )
            attribute.save(update_fields=["points"])
            task.completed_at = None
            earned_points = -points

        task.status = new_status
        task.save()
        new_owner_points = float(owner.recalculate_points_from_attributes())

    response = task_to_dict(task)
    if earned_points is not None:
        response["earned_points"] = earned_points
        response["owner_points"] = new_owner_points
        response["level_result"] = LevelSystem.handle_level_change(
            current_points=new_owner_points,
            previous_points=previous_owner_points,
        )
    return JsonResponse(response)


def delete_task(task):
    task.delete()
    return JsonResponse({"message": "Task deleted"})
