from django.urls import path
from .views import user_view, user_detail

app_name = "users"

urlpatterns = [
    path("users/", user_view, name="user_list"),
    path("users/<int:user_id>/", user_detail, name="user_detail"),
]
