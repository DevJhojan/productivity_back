
def task_to_dict(task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "owner_id": task.owner_id,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }
