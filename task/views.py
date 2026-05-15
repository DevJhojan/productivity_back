import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .task_serializer import task_to_dict
from .task_service import (list_tasks, create_task, get_task_or_404, update_task, patch_task, delete_task)
@csrf_exempt
def task_view(request):
    if request.method == "GET":
        return list_tasks()
    if request.method == "POST":
        return create_task(request)
    return JsonResponse({"error": "Method not allowed"}, status=405)
@csrf_exempt
def task_detail(request, task_id):
    task = get_task_or_404(task_id)
    if not task:
        return JsonResponse({"error": "Task not found"}, status=404)
    if request.method == "GET":
        return JsonResponse(task_to_dict(task))
    if request.method == "PUT":
        return update_task(task, json.loads(request.body))
    if request.method == "PATCH":
        return patch_task(task, json.loads(request.body))
    if request.method == "DELETE":
        return delete_task(task)
    return JsonResponse({"error": "Method not allowed"}, status=405)
