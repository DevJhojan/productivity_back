import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .users_serializer import user_to_dict
from .users_service import (list_users, create_user, _get_user_or_404, update_user, patch_user, delete_user)

@csrf_exempt
def user_view(request):
    if request.method == "GET":
        return list_users()
    if request.method == "POST":
        return create_user(request)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def user_detail(request, user_id):
    user, error = _get_user_or_404(user_id)
    if error:
        return error
    if request.method == "GET":
        return JsonResponse(user_to_dict(user))
    if request.method == "PUT":
        return update_user(user, json.loads(request.body))
    if request.method == "PATCH":
        return patch_user(user, json.loads(request.body))
    if request.method == "DELETE":
        return delete_user(user)
    return JsonResponse({"error": "Method not allowed"}, status=405)
