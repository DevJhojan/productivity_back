import json
from django.test import TestCase, RequestFactory
from .models_users import User
from .users_service import (
    create_user,
    update_user_partial,
    patch_user,
    delete_user,
    list_users,
)


def make_user(username="alice", document_number="123", points=0.0):
    return User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="pass",
        document_number=document_number,
        points=points,
    )


class CreateUserServiceTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _post(self, body: dict):
        request = self.factory.post(
            "/api/users/", json.dumps(body), content_type="application/json"
        )
        return create_user(request)

    def test_creates_user_successfully(self):
        response = self._post(
            {
                "username": "bob",
                "password": "pass",
                "email": "bob@test.com",
                "document_type": "CC",
                "document_number": "999",
            }
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data["username"], "bob")
        self.assertEqual(data["points"], 0.0)

    def test_missing_required_fields_returns_400(self):
        response = self._post({"username": "bob"})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("Missing required fields", data["error"])

    def test_duplicate_username_returns_400(self):
        make_user(username="dup", document_number="001")
        response = self._post(
            {
                "username": "dup",
                "password": "pass",
                "email": "dup2@test.com",
                "document_type": "CC",
                "document_number": "002",
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Username already exists", json.loads(response.content)["error"])

    def test_duplicate_email_returns_400(self):
        make_user(username="u1", document_number="010")
        # u1@test.com es el email generado por make_user para username="u1"
        response = self._post(
            {
                "username": "u2",
                "password": "pass",
                "email": "u1@test.com",
                "document_type": "CC",
                "document_number": "011",
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Email already exists", json.loads(response.content)["error"])

    def test_duplicate_document_number_returns_400(self):
        make_user(username="u3", document_number="777")
        response = self._post(
            {
                "username": "u4",
                "password": "pass",
                "email": "u4@test.com",
                "document_type": "CC",
                "document_number": "777",
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Document number already exists", json.loads(response.content)["error"]
        )


class UpdateUserServiceTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_put_updates_fields(self):
        response = update_user_partial(
            self.user,
            {
                "first_name": "Alice",
                "last_name": "Smith",
            },
        )
        data = json.loads(response.content)
        self.assertEqual(data["first_name"], "Alice")
        self.assertEqual(data["last_name"], "Smith")

    def test_patch_updates_only_provided_fields(self):
        response = patch_user(self.user, {"first_name": "Patched"})
        data = json.loads(response.content)
        self.assertEqual(data["first_name"], "Patched")
        self.assertEqual(data["username"], "alice")

    def test_patch_password_changes_password(self):
        patch_user(self.user, {"password": "newpass123"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass123"))


class DeleteUserServiceTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_delete_removes_user(self):
        user_id = self.user.id
        delete_user(self.user)
        self.assertFalse(User.objects.filter(id=user_id).exists())

    def test_delete_returns_message(self):
        response = delete_user(self.user)
        data = json.loads(response.content)
        self.assertEqual(data["message"], "User deleted")


class UserLevelStateTest(TestCase):
    def test_new_user_starts_at_nobody(self):
        user = make_user(points=0.0)
        state = user.get_level_state()
        self.assertEqual(state["level"], "Nobody")
        self.assertEqual(state["points"], 0.0)

    def test_level_state_reflects_points(self):
        user = make_user(points=1500.0)
        state = user.get_level_state()
        self.assertEqual(state["level"], "Novice")

    def test_serializer_includes_level_state(self):
        from .users_serializer import user_to_dict

        user = make_user(points=0.0)
        data = user_to_dict(user)
        self.assertIn("level_state", data)
        self.assertIn("points", data)
        self.assertEqual(data["points"], 0.0)
