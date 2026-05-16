# task_service.py
import json
from decimal import Decimal  # Asegura una inserción limpia en PostgreSQL
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from funcs.system_levels import LevelSystem
from .models_task import Task
from .task_serializer import task_to_dict


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
    data = json.loads(request.body)
    data = _clean_choices_data(data)  # Normalizamos aquí también

    task = Task.objects.create(
        title=data.get("title", ""),
        description=data.get("description", ""),
        status=data.get("status", Task.Status.PENDING),
        priority=data.get("priority", Task.Priority.NOT_IMPORTANT_NOT_URGENT),
        owner_id=data.get("owner_id"),
    )
    return JsonResponse(task_to_dict(task), status=201)


def get_task_or_404(task_id):
    try:
        return Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return None


def _map_task_type(task: Task) -> str:
    mapping = {
        Task.Priority.IMPORTANT_URGENT: "weekly_goal",
        Task.Priority.IMPORTANT_NOT_URGENT: "monthly_project",
        Task.Priority.NOT_IMPORTANT_URGENT: "daily_action",
        Task.Priority.NOT_IMPORTANT_NOT_URGENT: "daily_action",
    }
    return mapping.get(task.priority, "daily_action")


def _apply_task_fields(task, data, partial: bool):
    fields = ["title", "description", "status", "priority", "due_date", "owner_id"]

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

    calc = LevelSystem.complete_task_with_rules(
        current_points=float(owner.points),
        task_type=_map_task_type(task),
    )

    # Convertimos a string -> Decimal para evitar errores de precisión flotante en Postgres
    owner.points = Decimal(str(calc["total_points"]))
    owner.save(update_fields=["points"])
    return calc


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


def delete_task(task):
    task.delete()
    return JsonResponse({"message": "Task deleted"})
