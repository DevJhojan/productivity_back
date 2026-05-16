def goal_to_dict(goal) -> dict:
    attribute = goal.attribute
    return {
        "id": goal.id,
        "owner_id": goal.owner_id,
        "attribute": {
            "id": attribute.id,
            "name": attribute.name,
            "points": str(attribute.points),
        },
        "title": goal.title,
        "description": goal.description,
        "priority": goal.priority,
        "goal_subtype": goal.goal_subtype,
        "status": goal.status,
        "due_date": goal.due_date.isoformat() if goal.due_date else None,
        "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat(),
    }
