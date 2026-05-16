from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .habit_service import (
    list_habits,
    create_habit,
    get_habit,
    patch_habit,
    delete_habit,
    check_habit,
    uncheck_habit,
)


@csrf_exempt
def habit_list_view(request):
    if request.method == "GET":
        return list_habits(request)
    if request.method == "POST":
        return create_habit(request)
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def habit_detail_view(request, habit_id):
    if request.method == "GET":
        return get_habit(request, habit_id)
    if request.method == "PATCH":
        return patch_habit(request, habit_id)
    if request.method == "DELETE":
        return delete_habit(request, habit_id)
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def habit_check_view(request, habit_id):
    if request.method == "POST":
        return check_habit(request, habit_id)
    if request.method == "DELETE":
        return uncheck_habit(request, habit_id)
    return JsonResponse({"error": "Method not allowed"}, status=405)
