import json
from decimal import Decimal
from django.test import TestCase, RequestFactory
from users.models_users import User, UserAttribute
from .models_task import Task
from .task_service import (
    create_task,
    change_task_status,
    get_task_or_404,
    update_task,
    patch_task,
    delete_task,
)


def make_user(username="testuser", points=0.0):
    return User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="pass",
        document_number=username,
        points=points,
    )


def make_task(
    owner,
    status=Task.Status.PENDING,
    priority=Task.Priority.NOT_IMPORTANT_NOT_URGENT,
    attribute=None,
):
    if attribute is None:
        attribute = owner.attributes.get(name=UserAttribute.AttributeName.STRENGTH)
    return Task.objects.create(
        title="Test task",
        description="desc",
        status=status,
        priority=priority,
        owner=owner,
        attribute=attribute,
    )


class GetTaskOr404Test(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.task = make_task(self.owner)

    def test_returns_task_when_exists(self):
        result = get_task_or_404(self.task.id)
        self.assertEqual(result.id, self.task.id)

    def test_returns_none_when_not_exists(self):
        result = get_task_or_404(99999)
        self.assertIsNone(result)


class CreateTaskTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.factory = RequestFactory()

    def test_creates_task_with_defaults(self):
        body = json.dumps({"title": "New task", "owner_id": self.owner.id})
        request = self.factory.post(
            "/api/tasks/", body, content_type="application/json"
        )
        response = create_task(request)

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data["title"], "New task")
        self.assertEqual(data["status"], Task.Status.PENDING)

    def test_creates_task_with_explicit_status(self):
        body = json.dumps(
            {"title": "Task", "status": "IN_PROGRESS", "owner_id": self.owner.id}
        )
        request = self.factory.post(
            "/api/tasks/", body, content_type="application/json"
        )
        response = create_task(request)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "IN_PROGRESS")

    def test_creates_task_with_default_attribute_when_not_sent(self):
        body = json.dumps({"title": "Task", "owner_id": self.owner.id})
        request = self.factory.post(
            "/api/tasks/", body, content_type="application/json"
        )
        response = create_task(request)

        data = json.loads(response.content)
        self.assertIsNotNone(data["attribute_id"])


class PatchTaskLevelTest(TestCase):
    def setUp(self):
        self.owner = make_user(points=0.0)
        self.task = make_task(self.owner)

    def test_patch_to_completed_awards_points(self):
        response = patch_task(self.task, {"status": "COMPLETED"})
        data = json.loads(response.content)

        self.owner.refresh_from_db()
        self.assertIn("earned_points", data)
        self.assertEqual(data["earned_points"], 0.10)
        self.assertEqual(float(self.owner.points), 0.02)

    def test_patch_to_completed_sets_completed_at(self):
        patch_task(self.task, {"status": "COMPLETED"})
        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.completed_at)

    def test_patch_to_completed_includes_level_result(self):
        response = patch_task(self.task, {"status": "COMPLETED"})
        data = json.loads(response.content)
        self.assertIn("level_result", data)
        self.assertIn("owner_points", data)

    def test_patch_already_completed_does_not_award_points_again(self):
        self.task.status = Task.Status.COMPLETED
        self.task.save()
        self.owner.points = 1.0
        self.owner.save()

        patch_task(self.task, {"status": "COMPLETED"})
        self.owner.refresh_from_db()
        self.assertEqual(float(self.owner.points), 1.0)

    def test_patch_non_status_field_does_not_award_points(self):
        response = patch_task(self.task, {"title": "New title"})
        data = json.loads(response.content)

        self.owner.refresh_from_db()
        self.assertNotIn("earned_points", data)
        self.assertEqual(float(self.owner.points), 0.0)


class UpdateTaskLevelTest(TestCase):
    def setUp(self):
        self.owner = make_user(points=0.0)
        self.task = make_task(self.owner)

    def test_put_to_completed_awards_points(self):
        response = update_task(
            self.task, {"title": "T", "status": "COMPLETED", "owner_id": self.owner.id}
        )
        data = json.loads(response.content)

        self.owner.refresh_from_db()
        self.assertIn("earned_points", data)
        self.assertEqual(data["earned_points"], 0.10)
        self.assertEqual(float(self.owner.points), 0.02)

    def test_put_already_completed_does_not_double_award(self):
        self.task.status = Task.Status.COMPLETED
        self.task.save()
        self.owner.points = 5.0
        self.owner.save()

        update_task(
            self.task, {"title": "T", "status": "COMPLETED", "owner_id": self.owner.id}
        )
        self.owner.refresh_from_db()
        self.assertEqual(float(self.owner.points), 5.0)


class CustomStatusTransitionPointsPersistenceTest(TestCase):
    """Custom tests: transitioning to COMPLETED must persist points in DB."""

    def test_pending_to_completed_increments_and_persists_points(self):
        owner = make_user(username="pending_user", points=0.0)
        task = make_task(owner, status=Task.Status.PENDING)

        patch_task(task, {"status": "COMPLETED"})

        task.refresh_from_db()
        owner.refresh_from_db()

        self.assertEqual(task.status, Task.Status.COMPLETED)
        self.assertIsNotNone(task.completed_at)
        self.assertGreater(float(owner.points), 0.0)

    def test_in_progress_to_completed_increments_and_persists_points(self):
        owner = make_user(username="inprogress_user", points=0.0)
        task = make_task(owner, status=Task.Status.IN_PROGRESS)

        patch_task(task, {"status": "COMPLETED"})

        task.refresh_from_db()
        owner.refresh_from_db()

        self.assertEqual(task.status, Task.Status.COMPLETED)
        self.assertIsNotNone(task.completed_at)
        self.assertGreater(float(owner.points), 0.0)


class PointsParamsForTaskTest(TestCase):
    def test_task_model_always_maps_to_task_main_type(self):
        from .task_service import _get_points_params_for_task

        self.assertEqual(_get_points_params_for_task(), ("task", None))


class TaskAttributeRoutingTest(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner-attr")
        self.target_attribute = self.owner.attributes.get(
            name=UserAttribute.AttributeName.AGILITY
        )
        self.other_attribute = self.owner.attributes.get(
            name=UserAttribute.AttributeName.STRENGTH
        )
        self.task = make_task(self.owner, attribute=self.target_attribute)

    def test_completed_task_increments_only_linked_attribute(self):
        patch_task(self.task, {"status": "COMPLETED"})

        self.target_attribute.refresh_from_db()
        self.other_attribute.refresh_from_db()
        self.owner.refresh_from_db()

        self.assertEqual(float(self.target_attribute.points), 0.10)
        self.assertEqual(float(self.other_attribute.points), 0.00)
        self.assertEqual(float(self.owner.points), 0.02)

    def test_patch_rejects_attribute_from_other_owner(self):
        another_user = make_user(username="other-owner")
        another_attr = another_user.attributes.get(
            name=UserAttribute.AttributeName.PERCEPTION
        )

        response = patch_task(self.task, {"attribute_id": another_attr.id})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertIn("must belong", data["error"])


class DeleteTaskTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.task = make_task(self.owner)

    def test_delete_removes_task(self):
        task_id = self.task.id
        delete_task(self.task)
        self.assertIsNone(get_task_or_404(task_id))

    def test_delete_returns_message(self):
        response = delete_task(self.task)
        data = json.loads(response.content)
        self.assertEqual(data["message"], "Task deleted")


class TaskStatusEndpointTest(TestCase):
    def setUp(self):
        self.owner = make_user(username="status-owner")
        self.task = make_task(self.owner)
        self.factory = RequestFactory()

    def _change(self, status: str):
        request = self.factory.post(
            f"/api/tasks/{self.task.id}/status/",
            json.dumps({"status": status}),
            content_type="application/json",
        )
        return change_task_status(request, self.task)

    def test_pending_to_completed_adds_points(self):
        response = self._change("COMPLETED")
        data = json.loads(response.content)
        self.task.refresh_from_db()
        self.task.attribute.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["earned_points"], 0.10)
        self.assertEqual(self.task.attribute.points, Decimal("0.10"))

    def test_completed_to_pending_subtracts_points(self):
        self._change("COMPLETED")
        response = self._change("PENDING")
        data = json.loads(response.content)
        self.task.refresh_from_db()
        self.task.attribute.refresh_from_db()

        self.assertEqual(data["earned_points"], -0.10)
        self.assertEqual(self.task.attribute.points, Decimal("0.00"))
        self.assertIsNone(self.task.completed_at)

    def test_completed_to_in_progress_subtracts_points(self):
        self._change("COMPLETED")
        self._change("IN_PROGRESS")
        self.task.refresh_from_db()
        self.task.attribute.refresh_from_db()

        self.assertEqual(self.task.attribute.points, Decimal("0.00"))
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)
        self.assertIsNone(self.task.completed_at)

    def test_pending_to_in_progress_keeps_points(self):
        response = self._change("IN_PROGRESS")
        data = json.loads(response.content)
        self.task.refresh_from_db()
        self.task.attribute.refresh_from_db()

        self.assertNotIn("earned_points", data)
        self.assertEqual(self.task.attribute.points, Decimal("0.00"))

    def test_in_progress_to_pending_keeps_points(self):
        self._change("IN_PROGRESS")
        response = self._change("PENDING")
        data = json.loads(response.content)
        self.task.refresh_from_db()
        self.task.attribute.refresh_from_db()

        self.assertNotIn("earned_points", data)
        self.assertEqual(self.task.attribute.points, Decimal("0.00"))

    def test_completed_to_completed_no_changes(self):
        self._change("COMPLETED")
        response = self._change("COMPLETED")
        data = json.loads(response.content)
        self.task.refresh_from_db()
        self.task.attribute.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("earned_points", data)
        self.assertEqual(self.task.attribute.points, Decimal("0.10"))

    def test_invalid_status_returns_400(self):
        response = self._change("DONE")
        self.assertEqual(response.status_code, 400)

    def test_full_cycle_does_not_double_count(self):
        self._change("COMPLETED")
        self._change("PENDING")
        self._change("COMPLETED")
        self.task.refresh_from_db()
        self.task.attribute.refresh_from_db()

        self.assertEqual(self.task.attribute.points, Decimal("0.10"))
