def attributes_to_list(user):
    return [
        {
            "name": attr.name,
            "points": float(attr.points),
        }
        for attr in user.attributes.all().order_by("name")
    ]


def person_to_dict(user):
    return {
        "document_type": user.document_type,
        "document_number": user.document_number,
        "phone": user.phone,
        "address": user.address,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "points": float(user.points),
        "level_state": user.get_level_state(),
        "attributes": attributes_to_list(user),
        "person": person_to_dict(user),
    }
