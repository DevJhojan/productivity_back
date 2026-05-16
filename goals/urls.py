from django.urls import path
from .views import goal_list_view, goal_detail_view, goal_status_view

app_name = "goals"

urlpatterns = [
    path("", goal_list_view, name="goal_list"),
    path("<int:goal_id>/", goal_detail_view, name="goal_detail"),
    path("<int:goal_id>/status/", goal_status_view, name="goal_status"),
]
