import json
from django.http import JsonResponse
from .models_users import User
from .users_serializer import user_to_dict


def _load_json(request):
    try:
        return json.loads(request.body or "{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON body"}, status=400)


def _get_user_or_404(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None, JsonResponse({"error": "User not found"}, status=404)

def list_users():
    users = User.objects.all().order_by("-created_at")
    return JsonResponse([user_to_dict(user) for user in users], safe=False)


def create_user(request):
    data, error = _load_json(request)
    if error:
        return error

    required = ["username", "password", "email","document_type", "document_number"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return JsonResponse(
            {"error": f"Missing required fields: {', '.join(missing)}"},
            status=400,
        )

    if User.objects.filter(username=data["username"]).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)

    if User.objects.filter(email=data["email"]).exists():
        return JsonResponse({"error": "Email already exists"}, status=400)

    if User.objects.filter(document_number=data["document_number"]).exists():
        return JsonResponse({"error": "Document number already exists"}, status=400)

    user = User.objects.create_user(
        username=data["username"],
        email=data["email"],
        password=data["password"],
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        document_type=data.get("document_type"),
        document_number=data["document_number"],
        phone=data.get("phone", ""),
        address=data.get("address", ""),
        birth_date=data.get("birth_date"),
    )

    return JsonResponse(user_to_dict(user), status=201)


def update_user_partial(user, data):
    user.username = data.get("username", user.username)
    user.email = data.get("email", user.email)
    user.first_name = data.get("first_name", user.first_name)
    user.last_name = data.get("last_name", user.last_name)
    user.document_type = data.get("document_type", user.document_type)
    user.document_number = data.get("document_number", user.document_number)
    user.phone = data.get("phone", user.phone)
    user.address = data.get("address", user.address)
    user.birth_date = data.get("birth_date", user.birth_date)
    user.save()
    return JsonResponse(user_to_dict(user))

def patch_user(user, data):
    if "username" in data:
        user.username = data["username"]
    if "email" in data:
        user.email = data["email"]
    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    if "document_type" in data:
        user.document_type = data["document_type"]
    if "document_number" in data:
        user.document_number = data["document_number"]
    if "phone" in data:
        user.phone = data["phone"]
    if "address" in data:
        user.address = data["address"]
    if "birth_date" in data:
        user.birth_date = data["birth_date"]
    if "password" in data and data["password"]:
        user.set_password(data["password"])
    user.save()
    return JsonResponse(user_to_dict(user))

def delete_user(user):
    user.delete()
    return JsonResponse({"message": "User deleted"})
