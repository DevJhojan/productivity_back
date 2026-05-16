from django.urls import path
from .views import habit_list_view, habit_detail_view, habit_check_view

app_name = "habits"

urlpatterns = [
    path("", habit_list_view, name="habit_list"),
    path("<int:habit_id>/", habit_detail_view, name="habit_detail"),
    path("<int:habit_id>/check/", habit_check_view, name="habit_check"),
]
