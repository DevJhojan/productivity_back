import json
from django.test import TestCase, RequestFactory
from users.models_users import User
from .models_task import Task
from .task_service import (
    create_task,
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
    owner, status=Task.Status.PENDING, priority=Task.Priority.NOT_IMPORTANT_NOT_URGENT
):
    return Task.objects.create(
        title="Test task",
        description="desc",
        status=status,
        priority=priority,
        owner=owner,
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


class PatchTaskLevelTest(TestCase):
    def setUp(self):
        self.owner = make_user(points=0.0)
        self.task = make_task(self.owner)

    def test_patch_to_completed_awards_points(self):
        response = patch_task(self.task, {"status": "COMPLETED"})
        data = json.loads(response.content)

        self.owner.refresh_from_db()
        self.assertIn("earned_points", data)
        self.assertGreater(data["earned_points"], 0)
        self.assertGreater(float(self.owner.points), 0)

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
        self.assertGreater(float(self.owner.points), 0)

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


class MapTaskTypeTest(TestCase):
    def setUp(self):
        self.owner = make_user()

    def test_important_urgent_maps_to_weekly_goal(self):
        task = make_task(self.owner, priority=Task.Priority.IMPORTANT_URGENT)
        from .task_service import _map_task_type

        self.assertEqual(_map_task_type(task), "weekly_goal")

    def test_important_not_urgent_maps_to_monthly_project(self):
        task = make_task(self.owner, priority=Task.Priority.IMPORTANT_NOT_URGENT)
        from .task_service import _map_task_type

        self.assertEqual(_map_task_type(task), "monthly_project")

    def test_not_important_maps_to_daily_action(self):
        task = make_task(self.owner, priority=Task.Priority.NOT_IMPORTANT_NOT_URGENT)
        from .task_service import _map_task_type

        self.assertEqual(_map_task_type(task), "daily_action")


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
