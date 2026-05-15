import json
from django.http import JsonResponse
from .models import Task
from .task_serializer import task_to_dict
def list_tasks():
    tasks = Task.objects.all()
    return JsonResponse([task_to_dict(task) for task in tasks], safe=False)

def create_task(request):
    data = json.loads(request.body)
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

def update_task(task, data):
    task.title = data.get("title", task.title)
    task.description = data.get("description", task.description)
    task.status = data.get("status", task.status)
    task.priority = data.get("priority", task.priority)
    task.due_date = data.get("due_date", task.due_date)
    task.owner_id = data.get("owner_id", task.owner_id)
    task.save()
    return JsonResponse(task_to_dict(task))

def patch_task(task, data):
    if "title" in data:
        task.title = data["title"]
    if "description" in data:
        task.description = data["description"]
    if "status" in data:
        task.status = data["status"]
    if "priority" in data:
        task.priority = data["priority"]
    if "due_date" in data:
        task.due_date = data["due_date"]
    if "owner_id" in data:
        task.owner_id = data["owner_id"]
    task.save()
    return JsonResponse(task_to_dict(task))

def delete_task(task):
    task.delete()
    return JsonResponse({"message": "Task deleted"})
