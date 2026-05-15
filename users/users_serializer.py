def person_to_dict(person):
    return {
        "document_type": person.document_type,
        "document_number": person.document_number,
        "phone": person.phone,
        "address": person.address,
        "birth_date": person.birth_date.isoformat() if person.birth_date else None,
        "created_at": person.created_at.isoformat(),
        "updated_at": person.updated_at.isoformat(),
    }

def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "person": person_to_dict(user.person) if hasattr(user, 'person') else None,
    }
