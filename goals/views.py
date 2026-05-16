from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .goal_service import (
    list_goals,
    create_goal,
    get_goal,
    patch_goal,
    delete_goal,
)


@csrf_exempt
def goal_list_view(request):
    if request.method == "GET":
        return list_goals(request)
    if request.method == "POST":
        return create_goal(request)
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def goal_detail_view(request, goal_id):
    if request.method == "GET":
        return get_goal(request, goal_id)
    if request.method == "PATCH":
        return patch_goal(request, goal_id)
    if request.method == "DELETE":
        return delete_goal(request, goal_id)
    return JsonResponse({"error": "Method not allowed"}, status=405)
