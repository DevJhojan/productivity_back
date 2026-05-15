from django.urls import path
from .views import task_view, task_detail

app_name = "task"

urlpatterns = [
    path("tasks/", task_view, name="task_list"),
    path("tasks/<int:task_id>/", task_detail, name="task_detail"),
]

