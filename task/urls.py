from django.urls import path
from .views import task_view, task_detail, task_status_view

app_name = "task"

urlpatterns = [
    path("tasks/", task_view, name="task_list"),
    path("tasks/<int:task_id>/", task_detail, name="task_detail"),
    path("tasks/<int:task_id>/status/", task_status_view, name="task_status"),
]
