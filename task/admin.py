from django.contrib import admin
from .models_task import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'due_date', 'owner')
    list_filter = ('status', 'priority', 'due_date')
    search_fields = ('title', 'description', 'owner__username')
    ordering = ('-created_at',)


