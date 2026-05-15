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
        "person": person_to_dict(user) if hasattr(user, 'person') else None,
    }
