from django.contrib import admin
from .models_habit import Habit, HabitLog

admin.site.register(Habit)
admin.site.register(HabitLog)
